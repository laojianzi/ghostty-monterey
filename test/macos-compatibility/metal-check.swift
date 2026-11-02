import Foundation
import Metal
import IOSurface
import simd

func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    if !condition() {
        FileHandle.standardError.write(Data("FAIL: \(message)\n".utf8))
        exit(1)
    }
}

// Layouts mirror shaders.zig and Pipeline.autoAttribute, not Swift struct ABI.
let attributes: [String: ([(MTLVertexFormat, Int)], Int)] = [
    "cell_text": ([(.uint2, 0), (.uint2, 8), (.short2, 16), (.ushort2, 20),
                   (.uchar4, 24), (.uchar, 28), (.uchar, 29)], 32),
    "image": ([(.float2, 0), (.float2, 8), (.float4, 16), (.float2, 32)], 40),
    "bg_image": ([(.float, 0), (.uchar, 4)], 8)
]
let names = ["bg_color", "cell_bg", "cell_text", "image", "bg_image"]
let devices = MTLCopyAllDevices()
check(!devices.isEmpty, "No Metal device; not a passing skip")
let side = 8
let background: [UInt8] = [48, 96, 160, 192]
let cells: [[UInt8]] = [[255, 0, 0, 255], [0, 255, 0, 128], [0, 0, 255, 64], [127, 63, 191, 0]]
let glyphColor: [UInt8] = [204, 102, 51, 192]
let cursorColor: [UInt8] = [40, 180, 90, 255]
let masks: [UInt8] = [0, 64, 128, 255]
let texels: [[UInt8]] = [[32, 64, 96, 128], [120, 30, 60, 192],
                        [15, 45, 60, 64], [210, 150, 90, 255]]

func linearize(_ value: Double) -> Double {
    value <= 0.04045 ? value / 12.92 : pow((value + 0.055) / 1.055, 2.4)
}
func encode(_ value: Double) -> Double {
    value <= 0.0031308 ? value * 12.92 : 1.055 * pow(value, 1 / 2.4) - 0.055
}
func luminance(_ color: [Double]) -> Double {
    color[0] * 0.2126 + color[1] * 0.7152 + color[2] * 0.0722
}
func premultiplied(_ color: [UInt8], linear: Bool, displayP3: Bool) -> [Double] {
    let alpha = Double(color[3]) / 255
    var rgb = color.prefix(3).map { Double($0) / 255 }
    if linear || !displayP3 {
        rgb = rgb.map(linearize)
        if !displayP3 {
            // D50 sRGB -> XYZ -> Display P3 reference calculation in Double.
            let xyz = [0.4360747 * rgb[0] + 0.3850649 * rgb[1] + 0.1430804 * rgb[2],
                       0.2225045 * rgb[0] + 0.7168786 * rgb[1] + 0.0606169 * rgb[2],
                       0.0139322 * rgb[0] + 0.0971045 * rgb[1] + 0.7141733 * rgb[2]]
            rgb = [2.40414768 * xyz[0] - 0.99010704 * xyz[1] - 0.39759019 * xyz[2],
                   -0.84239098 * xyz[0] + 1.79905954 * xyz[1] + 0.01597023 * xyz[2],
                   0.04838763 * xyz[0] - 0.09752546 * xyz[1] + 1.27393636 * xyz[2]]
        }
        if !linear { rgb = rgb.map(encode) }
    }
    return rgb.map { $0 * alpha } + [alpha]
}

for device in devices {
    let library = try device.makeLibrary(URL: URL(fileURLWithPath: CommandLine.arguments[1]))
    let queue = device.makeCommandQueue()!
    var cases = 0
    for linear in [false, true] {
        let format: MTLPixelFormat = linear ? .bgra8Unorm_srgb : .bgra8Unorm
        var pipelines: [String: MTLRenderPipelineState] = [:]
        var uniformSize = 0
        var offsets: [String: Int] = [:]
        for name in names {
            let descriptor = MTLRenderPipelineDescriptor()
            descriptor.vertexFunction = library.makeFunction(name: attributes[name] == nil ? "full_screen_vertex" : name + "_vertex")
            descriptor.fragmentFunction = library.makeFunction(name: name + "_fragment")
            check(descriptor.vertexFunction != nil && descriptor.fragmentFunction != nil, "Missing \(name) functions")
            if let (fields, stride) = attributes[name] {
                let vertex = MTLVertexDescriptor()
                for (index, field) in fields.enumerated() {
                    vertex.attributes[index].format = field.0
                    vertex.attributes[index].offset = field.1
                    vertex.attributes[index].bufferIndex = 0
                }
                vertex.layouts[0].stride = stride
                vertex.layouts[0].stepFunction = .perInstance
                descriptor.vertexDescriptor = vertex
            }
            let color = descriptor.colorAttachments[0]!
            color.pixelFormat = format
            color.isBlendingEnabled = name != "bg_color"
            color.sourceRGBBlendFactor = .one
            color.sourceAlphaBlendFactor = .one
            color.destinationRGBBlendFactor = .oneMinusSourceAlpha
            color.destinationAlphaBlendFactor = .oneMinusSourceAlpha
            var reflection: MTLRenderPipelineReflection?
            pipelines[name] = try device.makeRenderPipelineState(descriptor: descriptor,
                options: [.argumentInfo, .bufferTypeInfo], reflection: &reflection)
            if name == "cell_bg" {
                let argument = reflection!.fragmentArguments!.first { $0.type == .buffer && $0.index == 1 }!
                uniformSize = argument.bufferDataSize
                for member in argument.bufferStructType!.members { offsets[member.name] = member.offset }
            }
        }
        // Reflection locates actual MSL members rather than trusting Swift alignment.
        check(uniformSize > 0 && offsets["bg_color"] != nil, "Missing uniform reflection")
        for extend: UInt8 in [0, 15] {
            for (mode, displayP3) in ["background", "cells", "composite", "glyph", "color-glyph", "image", "bg-image",
                                      "cursor", "cursor-glyph", "wide-cursor", "contrast", "contrast-exempt", "corrected-glyph"]
                .flatMap({ [($0, false), ($0, true)] }) {
                let textured = !["background", "cells", "composite"].contains(mode)
                let grayscale = textured && !["color-glyph", "image", "bg-image"].contains(mode)
                let uniforms = device.makeBuffer(length: uniformSize, options: .storageModeShared)!
                memset(uniforms.contents(), 0, uniformSize)
                func set<T>(_ name: String, _ value: T) {
                    uniforms.contents().advanced(by: offsets[name]!).storeBytes(of: value, as: T.self)
                }
                set("screen_size", SIMD2<Float>(8, 8))
                set("cell_size", SIMD2<Float>(3, 3))
                set("grid_size", SIMD2<UInt16>(2, 2))
                set("grid_padding", SIMD4<Float>(repeating: 1))
                set("padding_extend", extend)
                set("bg_color", SIMD4<UInt8>(background))
                set("use_display_p3", UInt8(displayP3 ? 1 : 0))
                set("use_linear_blending", UInt8(linear ? 1 : 0))
                set("cursor_pos", SIMD2<UInt16>(repeating: UInt16.max))
                set("cursor_color", SIMD4<UInt8>(cursorColor))
                if ["cursor", "cursor-glyph", "wide-cursor"].contains(mode) {
                    set("cursor_pos", SIMD2<UInt16>(0, 0))
                    set("cursor_wide", UInt8(mode == "wide-cursor" ? 1 : 0))
                }
                if ["contrast", "contrast-exempt"].contains(mode) { set("min_contrast", Float(21)) }
                if mode == "corrected-glyph" && linear { set("use_linear_correction", UInt8(1)) }
                set("projection_matrix", simd_float4x4(columns: (
                    SIMD4<Float>(0.25, 0, 0, 0), SIMD4<Float>(0, -0.25, 0, 0),
                    SIMD4<Float>(0, 0, 1, 0), SIMD4<Float>(-1, 1, 0, 1))))
                let cellBytes = cells.flatMap { $0 }
                let cellBuffer = cellBytes.withUnsafeBytes {
                    device.makeBuffer(bytes: $0.baseAddress!, length: $0.count, options: .storageModeShared)!
                }
                // Exercise the production IOSurface target/storage choice, then
                // copy through a synchronized buffer for CPU pixel assertions.
                let properties: [String: Any] = [kIOSurfaceWidth as String: side,
                    kIOSurfaceHeight as String: side, kIOSurfaceBytesPerElement as String: 4,
                    kIOSurfacePixelFormat as String: UInt32(0x42475241)]
                let surface = IOSurfaceCreate(properties as CFDictionary)!
                let textureDescriptor = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: format,
                    width: side, height: side, mipmapped: false)
                textureDescriptor.storageMode = device.supportsFamily(.apple1) ? .shared : .managed
                textureDescriptor.cpuCacheMode = .writeCombined
                textureDescriptor.usage = .renderTarget
                let texture = device.makeTexture(descriptor: textureDescriptor, iosurface: surface, plane: 0)!
                let pass = MTLRenderPassDescriptor()
                pass.colorAttachments[0].texture = texture
                pass.colorAttachments[0].loadAction = .clear
                pass.colorAttachments[0].storeAction = .store
                pass.colorAttachments[0].clearColor = MTLClearColorMake(0, 0, 0, 0)
                let command = queue.makeCommandBuffer()!
                let render = command.makeRenderCommandEncoder(descriptor: pass)!
                render.setFragmentBuffer(uniforms, offset: 0, index: 1)
                render.setFragmentBuffer(cellBuffer, offset: 0, index: 2)
                if mode != "cells" && !textured {
                    render.setRenderPipelineState(pipelines["bg_color"]!)
                    render.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: 3)
                }
                if mode != "background" && !textured {
                    render.setRenderPipelineState(pipelines["cell_bg"]!)
                    render.drawPrimitives(type: .triangle, vertexStart: 0, vertexCount: 3)
                }
                if textured {
                    func atlas(_ format: MTLPixelFormat, _ bytes: [UInt8], _ channels: Int) -> MTLTexture {
                        let descriptor = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: format,
                            width: 4, height: 4, mipmapped: false)
                        descriptor.storageMode = device.supportsFamily(.apple1) ? .shared : .managed
                        descriptor.usage = .shaderRead
                        let result = device.makeTexture(descriptor: descriptor)!
                        bytes.withUnsafeBytes {
                            result.replace(region: MTLRegionMake2D(0, 0, 4, 4), mipmapLevel: 0,
                                withBytes: $0.baseAddress!, bytesPerRow: 4 * channels)
                        }
                        return result
                    }
                    let mask = atlas(.r8Unorm, (0..<16).map { masks[($0 / 4 + $0 % 4) % 4] }, 1)
                    let color = atlas(.rgba8Unorm, (0..<16).flatMap { texels[($0 / 4 + $0 % 4) % 4] }, 4)
                    let vertex = device.makeBuffer(length: 40, options: .storageModeShared)!
                    memset(vertex.contents(), 0, 40)
                    func attribute<T>(_ offset: Int, _ value: T) {
                        vertex.contents().advanced(by: offset).storeBytes(of: value, as: T.self)
                    }
                    if mode == "bg-image" {
                        attribute(0, Float(0.5))
                        // Center + original size; repeat toggles with the padding case.
                        attribute(4, UInt8(4 | (3 << 4) | (extend == 15 ? 64 : 0)))
                        render.setRenderPipelineState(pipelines["bg_image"]!)
                        render.setVertexTexture(color, index: 0)
                        render.setFragmentTexture(color, index: 0)
                    } else if mode == "image" {
                        attribute(8, SIMD2<Float>(2, 2))
                        attribute(16, SIMD4<Float>(0, 0, 4, 4))
                        attribute(32, SIMD2<Float>(4, 4))
                        render.setRenderPipelineState(pipelines["image"]!)
                        render.setVertexTexture(color, index: 0)
                        render.setFragmentTexture(color, index: 0)
                    } else {
                        attribute(8, SIMD2<UInt32>(4, 4))
                        attribute(16, SIMD2<Int16>(2, 1))
                        attribute(24, SIMD4<UInt8>(glyphColor))
                        attribute(28, UInt8(mode == "color-glyph" ? 1 : 0))
                        if mode == "wide-cursor" {
                            attribute(20, SIMD2<UInt16>(1, 0))
                            attribute(16, SIMD2<Int16>(-1, 1))
                        }
                        if mode == "cursor-glyph" { attribute(29, UInt8(2)) }
                        if mode == "contrast-exempt" { attribute(29, UInt8(1)) }
                        render.setRenderPipelineState(pipelines["cell_text"]!)
                        render.setFragmentTexture(mask, index: 0)
                        render.setFragmentTexture(color, index: 1)
                    }
                    render.setVertexBuffer(vertex, offset: 0, index: 0)
                    render.setVertexBuffer(uniforms, offset: 0, index: 1)
                    render.setVertexBuffer(cellBuffer, offset: 0, index: 2)
                    render.drawPrimitives(type: mode == "bg-image" ? .triangle : .triangleStrip,
                        vertexStart: 0, vertexCount: mode == "bg-image" ? 3 : 4, instanceCount: 1)
                }
                render.endEncoding()
                let rowBytes = 256
                let readback = device.makeBuffer(length: rowBytes * side,
                    options: device.hasUnifiedMemory ? .storageModeShared : .storageModeManaged)!
                let blit = command.makeBlitCommandEncoder()!
                blit.copy(from: texture, sourceSlice: 0, sourceLevel: 0, sourceOrigin: MTLOrigin(),
                    sourceSize: MTLSize(width: side, height: side, depth: 1), to: readback,
                    destinationOffset: 0, destinationBytesPerRow: rowBytes, destinationBytesPerImage: rowBytes * side)
                if !device.hasUnifiedMemory { blit.synchronize(resource: readback) }
                blit.endEncoding()
                command.commit()
                command.waitUntilCompleted()
                check(command.status == .completed && command.error == nil, "GPU command failure: \(String(describing: command.error))")
                let pixels = readback.contents().assumingMemoryBound(to: UInt8.self)
                for y in 0..<side {
                    for x in 0..<side {
                        var expected = mode == "cells" || textured ? [Double](repeating: 0, count: 4) : premultiplied(background, linear: linear, displayP3: displayP3)
                        let inside = x >= 1 && x < 7 && y >= 1 && y < 7
                        if mode != "background" && !textured && (inside || extend == 15) {
                            let col = min(1, max(0, Int(floor(Double(x - 1) / 3))))
                            let row = min(1, max(0, Int(floor(Double(y - 1) / 3))))
                            let foreground = premultiplied(cells[row * 2 + col], linear: linear, displayP3: displayP3)
                            expected = zip(foreground, expected).map { $0 + $1 * (1 - foreground[3]) }
                        }
                        if mode == "bg-image" {
                            var image = [Double](repeating: 0, count: 4)
                            if extend == 15 || (x >= 2 && x < 6 && y >= 2 && y < 6) {
                                let tx = (x - 2 + 4) % 4
                                let ty = (y - 2 + 4) % 4
                                let sample = texels[(tx + ty) % 4].map { Double($0) / 255 }
                                image = sample.prefix(3).map { (linear ? $0 : encode($0)) * sample[3] } + [sample[3]]
                                image = image.map { $0 * 0.5 }
                            }
                            let opaque = premultiplied(Array(background.prefix(3)) + [255], linear: linear, displayP3: displayP3)
                            let remaining = 1.0 - image[3]
                            let opacity = Double(background[3]) / 255.0
                            expected = (0..<4).map { (image[$0] + opaque[$0] * remaining) * opacity }
                        } else if textured && x >= 2 && x < 6 && y >= 2 && y < 6 {
                            let index = (x - 2 + y - 2) % 4
                            if grayscale {
                                let cursor = mode == "cursor" || mode == "wide-cursor"
                                var fg = premultiplied(cursor ? cursorColor : glyphColor, linear: true, displayP3: displayP3)
                                let cellBG = premultiplied(cells[0], linear: true, displayP3: displayP3)
                                let globalBG = premultiplied(background, linear: true, displayP3: displayP3)
                                let bg = zip(cellBG, globalBG).map { $0 + $1 * (1 - cellBG[3]) }
                                if mode == "contrast" {
                                    let whiteRatio = 1.05 / (luminance(bg) + 0.05)
                                    let blackRatio = (luminance(bg) + 0.05) / 0.05
                                    fg = whiteRatio > blackRatio ? [1, 1, 1, 1] : [0, 0, 0, 1]
                                }
                                var mask = Double(masks[index]) / 255
                                if mode == "corrected-glyph" && linear {
                                    let foregroundLuminance = luminance(fg)
                                    let backgroundLuminance = luminance(bg)
                                    if abs(foregroundLuminance - backgroundLuminance) > 0.001 {
                                        let blended = linearize(encode(foregroundLuminance) * mask + encode(backgroundLuminance) * (1 - mask))
                                        mask = max(0, min(1, (blended - backgroundLuminance) / (foregroundLuminance - backgroundLuminance)))
                                    }
                                }
                                if !linear {
                                    fg = fg.prefix(3).map { encode($0 / fg[3]) * fg[3] } + [fg[3]]
                                }
                                expected = fg.map { $0 * mask }
                            } else {
                                let sample = texels[index].map { Double($0) / 255 }
                                let alpha = sample[3]
                                if mode == "image" {
                                    expected = sample.prefix(3).map { (linear ? $0 : encode($0)) * alpha } + [alpha]
                                } else {
                                    expected = sample.prefix(3).map { linear ? $0 : encode($0 / alpha) * alpha } + [alpha]
                                }
                            }
                        }
                        for (channel, rgba) in [2, 1, 0, 3].enumerated() {
                            let value = linear && rgba < 3 ? encode(expected[rgba]) : expected[rgba]
                            let byte = Int((max(0, min(1, value)) * 255).rounded())
                            let actual = Int(pixels[y * rowBytes + x * 4 + channel])
                            check(abs(byte - actual) <= 2,
                                "pixel mismatch \(device.name) linear=\(linear) p3=\(displayP3) \(mode) extend=\(extend) (\(x),\(y)) channel=\(channel): \(actual) != \(byte)")
                        }
                    }
                }
                cases += 1
            }
        }
    }
    print("PASS: \(device.name): 10 pipelines, \(cases) IOSurface draws/readbacks (background/cells/composite, grayscale/color glyphs, cursor/wide/exempt, contrast, linear correction, image/background-image, alpha, padding/repeat, gamma/linear, sRGB/P3)")
}
