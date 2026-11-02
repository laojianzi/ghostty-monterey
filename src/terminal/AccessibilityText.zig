//! On-demand accessibility text mapping. No work is performed by the render path.
const std = @import("std");
const assert = std.debug.assert;
const Allocator = std.mem.Allocator;
const Screen = @import("Screen.zig");
const Selection = @import("Selection.zig");
const SelectionString = Screen.SelectionString;
const ScreenFormatter = @import("formatter.zig").ScreenFormatter;

/// Count UTF-16 code units in the same plain text as selectionString, without
/// allocating that text or a byte-to-pin map. AppKit text ranges use these units.
pub fn selectionUtf16Length(self: *Screen, opts: SelectionString) std.Io.Writer.Error!usize {
    var buffer: [256]u8 = undefined;
    var counter: Utf16Counter = .{ .writer = .{
        .vtable = &.{ .drain = Utf16Counter.drain },
        .buffer = &buffer,
    } };
    var formatter: ScreenFormatter = .init(self, .{
        .emit = .plain,
        .unwrap = true,
        .trim = opts.trim,
    });
    formatter.content = .{ .selection = opts.sel };
    try formatter.format(&counter.writer);
    return counter.count + Utf16Counter.units(counter.writer.buffered());
}

pub const Utf16Range = extern struct {
    location: usize,
    length: usize,
};

/// Map a contiguous selection into the untrimmed, unwrapped screen text.
/// The caller must keep the screen unchanged for both formatter passes.
/// Rectangle callers must pass each selected row separately: a rectangle is
/// generally not representable by one range in the screen's text.
pub fn selectionUtf16Range(self: *Screen, sel: Selection) std.Io.Writer.Error!Utf16Range {
    const top = sel.topLeft(self);
    const bottom = sel.bottomRight(self);
    assert(!sel.rectangle or (top.node == bottom.node and top.y == bottom.y));
    const length = try selectionUtf16Length(self, .{ .sel = sel, .trim = false });
    // A rectangular row excludes the wide glyph after a spacer head, whereas
    // a normal prefix formatter extends onto that glyph on the following row.
    var prefix_end = bottom;
    if (sel.rectangle and bottom.rowAndCell().cell.wide == .spacer_head) prefix_end.x -|= 1;
    const end = try selectionUtf16Length(self, .{
        .sel = .init(self.pages.getTopLeft(.screen), prefix_end, false),
        .trim = false,
    });
    assert(end >= length);
    return .{ .location = end - length, .length = length };
}

/// Owned accessibility text and selection ranges from one screen state.
/// Callers must hold the terminal state lock throughout construction.
pub const TextSnapshot = struct {
    text: [:0]const u8,
    selected_text: [:0]const u8,
    ranges: []const Utf16Range,

    pub fn deinit(self: TextSnapshot, alloc: Allocator) void {
        alloc.free(self.text);
        alloc.free(self.selected_text);
        alloc.free(self.ranges);
    }
};

pub fn textSnapshot(self: *Screen, alloc: Allocator) (Allocator.Error || std.Io.Writer.Error)!TextSnapshot {
    const text = if (self.pages.getBottomRight(.screen)) |bottom|
        try self.selectionString(alloc, .{
            .sel = .init(self.pages.getTopLeft(.screen), bottom, false),
            .trim = false,
        })
    else
        try alloc.dupeSentinel(u8, "", 0);
    errdefer alloc.free(text);
    const selected_text = if (self.selection) |sel|
        try self.selectionString(alloc, .{ .sel = sel, .trim = false })
    else
        try alloc.dupeSentinel(u8, "", 0);
    errdefer alloc.free(selected_text);
    var ranges: std.ArrayList(Utf16Range) = .empty;
    errdefer ranges.deinit(alloc);
    if (self.selection) |sel| {
        if (!sel.rectangle) {
            try ranges.append(alloc, try selectionUtf16Range(self, sel));
        } else {
            const top = sel.topLeft(self);
            const bottom = sel.bottomRight(self);
            const PageFormatter = @import("formatter.zig").PageFormatter;
            var prefix = self.pages.getTopLeft(.screen);
            var prefix_state: PageFormatter.TrailingState = .empty;
            var buffer: [256]u8 = undefined;
            var counter: Utf16Counter = .{ .writer = .{
                .vtable = &.{ .drain = Utf16Counter.drain },
                .buffer = &buffer,
            } };
            var rows = top.rowIterator(.right_down, bottom);
            while (rows.next()) |row| {
                var left = row;
                left.x = @min(top.x, row.node.cols() - 1);
                var right = row;
                right.x = @min(bottom.x, row.node.cols() - 1);
                const length = try selectionUtf16Length(self, .{
                    .sel = .init(left, right, true),
                    .trim = false,
                });
                if (length == 0) continue;

                var end = right;
                if (end.rowAndCell().cell.wide == .spacer_head) end.x -|= 1;
                // Consume completed rows exactly once. The endpoint row is
                // counted speculatively, without committing its partial state.
                while (prefix.node != end.node or prefix.y < end.y) {
                    var formatter: PageFormatter = .init(prefix.node.page(), .{
                        .emit = .plain,
                        .unwrap = true,
                        .trim = false,
                    });
                    formatter.start_y = prefix.y;
                    formatter.end_y = if (prefix.node == end.node) end.y - 1 else prefix.node.rows() - 1;
                    prefix_state = try formatter.continuePlain(&counter.writer, prefix_state);
                    if (prefix.node == end.node) {
                        prefix.y = end.y;
                    } else {
                        prefix = .{ .node = prefix.node.next.? };
                    }
                }
                var partial: PageFormatter = .init(end.node.page(), .{
                    .emit = .plain,
                    .unwrap = true,
                    .trim = false,
                });
                partial.start_y = end.y;
                partial.end_x = end.x;
                partial.end_y = end.y;
                try counter.writer.flush();
                const prefix_count = counter.count;
                _ = try partial.continuePlain(&counter.writer, prefix_state);
                const end_offset = counter.count + Utf16Counter.units(counter.writer.buffered());
                counter.count = prefix_count;
                counter.writer.end = 0;
                assert(end_offset >= length);
                try ranges.append(alloc, .{ .location = end_offset - length, .length = length });
            }
        }
    }
    return .{ .text = text, .selected_text = selected_text, .ranges = try ranges.toOwnedSlice(alloc) };
}

const Utf16Counter = struct {
    writer: std.Io.Writer,
    count: usize = 0,

    fn units(bytes: []const u8) usize {
        var result: usize = 0;
        // The formatter emits valid UTF-8. Count leading bytes only, so a
        // codepoint split across writer drains needs no carry buffer.
        for (bytes) |byte| {
            if (byte & 0xc0 == 0x80) continue;
            result += if (byte >= 0xf0) @as(usize, 2) else 1;
        }
        return result;
    }

    fn drain(writer: *std.Io.Writer, data: []const []const u8, splat: usize) std.Io.Writer.Error!usize {
        const self: *Utf16Counter = @alignCast(@fieldParentPtr("writer", writer));
        self.count += units(writer.buffered());
        writer.end = 0;
        var written: usize = 0;
        for (data[0 .. data.len - 1]) |bytes| {
            self.count += units(bytes);
            written += bytes.len;
        }
        const pattern = data[data.len - 1];
        self.count += units(pattern) * splat;
        return written + pattern.len * splat;
    }
};

test "Screen UTF-16 counter writer boundaries" {
    const testing = std.testing;
    const alloc = testing.allocator;
    const text = "a\u{4e2d}\u{1f680}e\u{301}\u{1f469}\u{200d}\u{1f4bb}\n";
    const expected = try std.unicode.utf8ToUtf16LeAlloc(alloc, text);
    defer alloc.free(expected);
    var storage: [32]u8 = undefined;
    for (0..storage.len + 1) |size_| {
        var counter: Utf16Counter = .{ .writer = .{
            .vtable = &.{ .drain = Utf16Counter.drain },
            .buffer = storage[0..size_],
        } };
        // Deliberately split UTF-8 sequences across writes and drains.
        for (0..17) |_| {
            for (text) |byte| try counter.writer.writeByte(byte);
        }
        try testing.expectEqual(expected.len * 17, counter.count + Utf16Counter.units(counter.writer.buffered()));
        try counter.writer.flush();
        try testing.expectEqual(expected.len * 17, counter.count);
    }
    var counter: Utf16Counter = .{ .writer = .{
        .vtable = &.{ .drain = Utf16Counter.drain },
        .buffer = &.{},
    } };
    // Cover the writer's vectored-data and repeated-final-pattern contract.
    const written = try Utf16Counter.drain(&counter.writer, &.{ "ab", "\xe4\xb8", "\xad", "\xf0\x9f\x9a\x80" }, 3);
    try testing.expectEqual(@as(usize, 17), written);
    try testing.expectEqual(@as(usize, 9), counter.count);
}

const point = @import("point.zig");

test "StringMap selection range mapping feasibility" {
    const testing = std.testing;
    const alloc = testing.allocator;
    const Terminal = @import("Terminal.zig");
    const Case = struct {
        input: []const u8,
        cols: u16 = 20,
        rows: u16 = 5,
        start: point.Coordinate,
        end: point.Coordinate,
        rectangle: bool = false,
        expected: []const u8,
        contiguous: bool = true,
        utf16_start: ?usize = null,
        mapped_suffix: []const u8 = "",
        membership_matches: bool = true,
    };
    // These checks exercise the existing formatter map, not a new AX API.
    // In particular, identical text must be located by pins, not string search.
    const cases = [_]Case{
        .{ .input = "same same", .start = .{ .x = 5, .y = 0 }, .end = .{ .x = 8, .y = 0 }, .expected = "same" },
        .{ .input = "same\r\nsame", .start = .{ .x = 0, .y = 1 }, .end = .{ .x = 3, .y = 1 }, .expected = "same" },
        .{ .input = "same same", .start = .{ .x = 8, .y = 0 }, .end = .{ .x = 5, .y = 0 }, .expected = "same" },
        .{ .input = "a\u{1f680}e\u{301}z", .start = .{ .x = 1, .y = 0 }, .end = .{ .x = 3, .y = 0 }, .expected = "\u{1f680}e\u{301}" },
        .{ .input = "a\u{1f680}z", .start = .{ .x = 2, .y = 0 }, .end = .{ .x = 2, .y = 0 }, .expected = "\u{1f680}", .utf16_start = 1, .membership_matches = false },
        .{ .input = "abc\r\ndef", .start = .{ .x = 1, .y = 0 }, .end = .{ .x = 1, .y = 1 }, .expected = "bc\nde" },
        .{ .input = "\r\nsame", .start = .{ .x = 0, .y = 0 }, .end = .{ .x = 3, .y = 1 }, .expected = "\nsame" },
        .{ .input = "a   b", .start = .{ .x = 1, .y = 0 }, .end = .{ .x = 3, .y = 0 }, .expected = "   " },
        .{ .input = "abcdefgh", .cols = 5, .start = .{ .x = 3, .y = 0 }, .end = .{ .x = 1, .y = 1 }, .expected = "defg" },
        .{ .input = "\u{1f680}e\u{301}same same", .start = .{ .x = 8, .y = 0 }, .end = .{ .x = 11, .y = 0 }, .expected = "same", .utf16_start = 9 },
        .{ .input = "old\r\nsame\r\nnew\r\nsame\r\nend", .rows = 2, .start = .{ .x = 0, .y = 1 }, .end = .{ .x = 3, .y = 1 }, .expected = "same", .utf16_start = 4, .mapped_suffix = "\n" },
        .{ .input = "old\r\nsame\r\nnew\r\nsame\r\nend", .rows = 2, .start = .{ .x = 0, .y = 1 }, .end = .{ .x = 3, .y = 3 }, .expected = "same\nnew\nsame", .utf16_start = 4, .mapped_suffix = "\n" },
        .{ .input = "abcde\r\nfghij", .start = .{ .x = 1, .y = 0 }, .end = .{ .x = 2, .y = 1 }, .rectangle = true, .expected = "bc\ngh", .contiguous = false },
    };
    for (cases) |case| {
        var t = try Terminal.init(testing.io, alloc, .{ .cols = case.cols, .rows = case.rows });
        defer t.deinit(alloc);
        var stream = t.vtStream();
        defer stream.deinit();
        stream.nextSlice(case.input);
        const screen = t.screens.active;
        const whole = Selection.init(screen.pages.getTopLeft(.screen), screen.pages.getBottomRight(.screen).?, false);
        const map = try screen.selectionStringMap(alloc, .{ .sel = whole, .trim = false });
        defer map.deinit(alloc);
        const selection = Selection.init(
            screen.pages.pin(.{ .screen = case.start }).?,
            screen.pages.pin(.{ .screen = case.end }).?,
            case.rectangle,
        );
        const selected = try screen.selectionString(alloc, .{ .sel = selection, .trim = false });
        defer alloc.free(selected);
        try testing.expectEqualStrings(case.expected, selected);
        const selected_utf16 = try std.unicode.utf8ToUtf16LeAlloc(alloc, selected);
        defer alloc.free(selected_utf16);
        try testing.expectEqual(selected_utf16.len, try selectionUtf16Length(screen, .{ .sel = selection, .trim = false }));
        const trimmed = try screen.selectionString(alloc, .{ .sel = selection, .trim = true });
        defer alloc.free(trimmed);
        const trimmed_utf16 = try std.unicode.utf8ToUtf16LeAlloc(alloc, trimmed);
        defer alloc.free(trimmed_utf16);
        try testing.expectEqual(trimmed_utf16.len, try selectionUtf16Length(screen, .{ .sel = selection, .trim = true }));
        const selected_map = try screen.selectionStringMap(alloc, .{ .sel = selection, .trim = false });
        defer selected_map.deinit(alloc);
        if (case.contiguous) {
            const prefix_selection = Selection.init(
                screen.pages.getTopLeft(.screen),
                selection.bottomRight(screen),
                false,
            );
            const prefix_text = try screen.selectionString(alloc, .{ .sel = prefix_selection, .trim = false });
            defer alloc.free(prefix_text);
            try testing.expect(std.mem.endsWith(u8, prefix_text, selected));
            const prefix_begin = prefix_text.len - selected.len;
            const prefix_utf16 = try std.unicode.utf8ToUtf16LeAlloc(alloc, prefix_text);
            defer alloc.free(prefix_utf16);
            try testing.expectEqual(prefix_utf16.len, try selectionUtf16Length(screen, .{ .sel = prefix_selection, .trim = false }));
            try testing.expectEqualStrings(selected, map.string[prefix_begin..][0..selected.len]);
            // The same prefix can be counted without allocating either its
            // text or a per-byte pin map. Keep only a bounded writer buffer.
            var buffer: [31]u8 = undefined;
            var counter: std.Io.Writer.Discarding = .init(&buffer);
            var formatter: @import("formatter.zig").ScreenFormatter = .init(screen, .{
                .emit = .plain,
                .unwrap = true,
                .trim = false,
            });
            formatter.content = .{ .selection = prefix_selection };
            try formatter.format(&counter.writer);
            try testing.expectEqual(prefix_text.len, counter.fullCount());
            // The selected formatter resolves spacer tails to their glyph's
            // leading cell. Locate that serialized origin, not the raw pin.
            const origin = selected_map.map.get(0).?;
            const begin = for (0..map.string.len) |offset| {
                if (map.map.get(offset).?.eql(origin)) break offset;
            } else return error.MissingSerializedOrigin;
            try testing.expect(begin + selected.len <= map.string.len);
            try testing.expectEqualStrings(selected, map.string[begin..][0..selected.len]);
            try testing.expectEqual(begin, prefix_begin);
            const actual_range = try selectionUtf16Range(screen, selection);
            const expected_prefix = try std.unicode.utf8ToUtf16LeAlloc(alloc, map.string[0..begin]);
            defer alloc.free(expected_prefix);
            try testing.expectEqual(expected_prefix.len, actual_range.location);
            try testing.expectEqual(selected_utf16.len, actual_range.length);
            if (case.utf16_start) |expected| {
                const prefix = try std.unicode.utf8ToUtf16LeAlloc(alloc, map.string[0..begin]);
                defer alloc.free(prefix);
                try testing.expectEqual(expected, prefix.len);
            }
        }
        var first: ?usize = null;
        var end: usize = 0;
        var selected_bytes: usize = 0;
        for (0..map.string.len) |offset| {
            if (!selection.contains(screen, map.map.get(offset).?)) continue;
            if (first == null) first = offset;
            end = offset + 1;
            selected_bytes += 1;
        }
        if (!case.membership_matches) {
            try testing.expect(first == null);
            continue;
        }
        const begin = first orelse return error.MissingSelectionMapping;
        if (case.contiguous) {
            try testing.expectEqual(selected_bytes, end - begin);
            // A formatter-inserted newline can share the final text cell's pin.
            // Membership alone therefore cannot recover an exact text range.
            const expected_map = try std.mem.concat(alloc, u8, &.{ selected, case.mapped_suffix });
            defer alloc.free(expected_map);
            try testing.expectEqualStrings(expected_map, map.string[begin..end]);
            if (case.utf16_start) |expected| {
                const prefix = try std.unicode.utf8ToUtf16LeAlloc(alloc, map.string[0..begin]);
                defer alloc.free(prefix);
                try testing.expectEqual(expected, prefix.len);
            }
            if (std.mem.startsWith(u8, case.input, "same")) {
                try testing.expect(begin > 0);
            }
        } else {
            try testing.expect(selected_bytes < end - begin);
            try testing.expect(!std.mem.eql(u8, selected, map.string[begin..end]));
            // Rectangle serialization joins disjoint row spans with newlines.
            // Verify each actual row span against its source pins separately.
            var rows = std.mem.splitScalar(u8, selected, '\n');
            var selected_offset: usize = 0;
            var previous_end: usize = 0;
            while (rows.next()) |row| {
                const origin = selected_map.map.get(selected_offset).?;
                const row_begin = for (0..map.string.len) |offset| {
                    if (map.map.get(offset).?.eql(origin)) break offset;
                } else return error.MissingRectangleOrigin;
                try testing.expect(row_begin >= previous_end);
                try testing.expectEqualStrings(row, map.string[row_begin..][0..row.len]);
                const row_end_pin = selected_map.map.get(selected_offset + row.len - 1).?;
                const prefix = try screen.selectionString(alloc, .{
                    .sel = .init(screen.pages.getTopLeft(.screen), row_end_pin, false),
                    .trim = false,
                });
                defer alloc.free(prefix);
                try testing.expect(std.mem.endsWith(u8, prefix, row));
                try testing.expectEqual(row_begin, prefix.len - row.len);
                const row_selection = Selection.init(origin, row_end_pin, true);
                const actual_range = try selectionUtf16Range(screen, row_selection);
                const expected_prefix = try std.unicode.utf8ToUtf16LeAlloc(alloc, map.string[0..row_begin]);
                defer alloc.free(expected_prefix);
                const expected_row = try std.unicode.utf8ToUtf16LeAlloc(alloc, row);
                defer alloc.free(expected_row);
                try testing.expectEqual(expected_prefix.len, actual_range.location);
                try testing.expectEqual(expected_row.len, actual_range.length);
                previous_end = row_begin + row.len;
                selected_offset += row.len + 1;
            }
        }
    }
}

test "StringMap selection prefix exhaustive boundaries" {
    const testing = std.testing;
    const alloc = testing.allocator;
    const Terminal = @import("Terminal.zig");
    for ([_][]const u8{ "abc\r\ndef", "a\u{1f680}z\r\ne\u{301}", "same same", "abcdefghijk" }) |input| {
        var t = try Terminal.init(testing.io, alloc, .{ .cols = 6, .rows = 3 });
        defer t.deinit(alloc);
        var stream = t.vtStream();
        defer stream.deinit();
        stream.nextSlice(input);
        const screen = t.screens.active;
        const top = screen.pages.getTopLeft(.screen);
        const bottom = screen.pages.getBottomRight(.screen).?;
        const whole = try screen.selectionString(alloc, .{ .sel = .init(top, bottom, false), .trim = false });
        defer alloc.free(whole);
        const last = screen.pages.pointFromPin(.screen, bottom).?.screen;
        const count = @as(usize, last.y) * 6 + last.x + 1;
        for (0..count) |start| {
            for (start..count) |end| {
                const a = screen.pages.pin(.{ .screen = .{ .x = @intCast(start % 6), .y = @intCast(start / 6) } }).?;
                const b = screen.pages.pin(.{ .screen = .{ .x = @intCast(end % 6), .y = @intCast(end / 6) } }).?;
                const selected = try screen.selectionString(alloc, .{ .sel = .init(a, b, false), .trim = false });
                defer alloc.free(selected);
                const prefix = try screen.selectionString(alloc, .{ .sel = .init(top, b, false), .trim = false });
                defer alloc.free(prefix);
                const selected_utf16 = try std.unicode.utf8ToUtf16LeAlloc(alloc, selected);
                defer alloc.free(selected_utf16);
                const prefix_utf16 = try std.unicode.utf8ToUtf16LeAlloc(alloc, prefix);
                defer alloc.free(prefix_utf16);
                try testing.expectEqual(selected_utf16.len, try selectionUtf16Length(screen, .{ .sel = .init(a, b, false), .trim = false }));
                try testing.expectEqual(prefix_utf16.len, try selectionUtf16Length(screen, .{ .sel = .init(top, b, false), .trim = false }));
                try testing.expect(std.mem.endsWith(u8, prefix, selected));
                const offset = prefix.len - selected.len;
                try testing.expect(offset + selected.len <= whole.len);
                try testing.expectEqualStrings(selected, whole[offset..][0..selected.len]);
                const actual_range = try selectionUtf16Range(screen, .init(a, b, false));
                try testing.expectEqual(prefix_utf16.len - selected_utf16.len, actual_range.location);
                try testing.expectEqual(selected_utf16.len, actual_range.length);
            }
        }
    }
}

test "StringMap rectangle UTF-16 row ranges" {
    const testing = std.testing;
    const alloc = testing.allocator;
    const Terminal = @import("Terminal.zig");
    for ([_][]const u8{
        "abcdef\r\nghijkl",
        "a\u{1f680}e\u{301}z\r\n\u{4e2d}xyz",
        "ab\r\n\r\ncdef",
        "same\r\nsame\r\nsame\r\nsame",
        "abcdefghijklmno\u{1f680}pq\r\n\r\nend",
    }) |input| {
        var t = try Terminal.init(testing.io, alloc, .{ .cols = 8, .rows = 2 });
        defer t.deinit(alloc);
        var stream = t.vtStream();
        defer stream.deinit();
        stream.nextSlice(input);
        const screen = t.screens.active;
        const top = screen.pages.getTopLeft(.screen);
        const bottom = screen.pages.getBottomRight(.screen).?;
        const whole = try screen.selectionString(alloc, .{ .sel = .init(top, bottom, false), .trim = false });
        defer alloc.free(whole);
        const utf16 = try std.unicode.utf8ToUtf16LeAlloc(alloc, whole);
        defer alloc.free(utf16);
        const last_y = screen.pages.pointFromPin(.screen, bottom).?.screen.y;
        for (0..8) |left| {
            for (left..8) |right| {
                try screen.select(.init(
                    screen.pages.pin(.{ .screen = .{ .x = @intCast(left), .y = 0 } }).?,
                    screen.pages.pin(.{ .screen = .{ .x = @intCast(right), .y = last_y } }).?,
                    true,
                ));
                const snapshot = try textSnapshot(screen, alloc);
                defer snapshot.deinit(alloc);
                var range_index: usize = 0;
                var previous_end: usize = 0;
                for (0..last_y + 1) |y| {
                    const a = screen.pages.pin(.{ .screen = .{ .x = @intCast(left), .y = @intCast(y) } }).?;
                    const b = screen.pages.pin(.{ .screen = .{ .x = @intCast(right), .y = @intCast(y) } }).?;
                    const row = Selection.init(a, b, true);
                    const text = try screen.selectionString(alloc, .{ .sel = row, .trim = false });
                    defer alloc.free(text);
                    const expected = try std.unicode.utf8ToUtf16LeAlloc(alloc, text);
                    defer alloc.free(expected);
                    const range = try selectionUtf16Range(screen, row);
                    if (range.length > 0) {
                        try testing.expectEqual(range, snapshot.ranges[range_index]);
                        range_index += 1;
                    }
                    try testing.expect(range.location >= previous_end);
                    try testing.expect(range.location + range.length <= utf16.len);
                    try testing.expectEqualSlices(u16, expected, utf16[range.location..][0..range.length]);
                    previous_end = range.location + range.length;
                }
                try testing.expectEqual(range_index, snapshot.ranges.len);
            }
        }
    }
}

test "StringMap UTF-16 range tracked selection after reflow" {
    const testing = std.testing;
    const alloc = testing.allocator;
    const Terminal = @import("Terminal.zig");
    var t = try Terminal.init(testing.io, alloc, .{ .cols = 20, .rows = 3 });
    defer t.deinit(alloc);
    var stream = t.vtStream();
    defer stream.deinit();
    stream.nextSlice("same \u{1f680} same\r\nlast");
    const screen = t.screens.active;
    try screen.select(.init(
        screen.pages.pin(.{ .screen = .{ .x = 8, .y = 0 } }).?,
        screen.pages.pin(.{ .screen = .{ .x = 11, .y = 0 } }).?,
        false,
    ));
    for ([_]u16{ 20, 6, 12, 4, 20 }) |cols| {
        try t.resize(alloc, .{ .cols = cols, .rows = 3 });
        const selection = screen.selection.?;
        const selected = try screen.selectionString(alloc, .{ .sel = selection, .trim = false });
        defer alloc.free(selected);
        try testing.expectEqualStrings("same", selected);
        const whole = try screen.selectionString(alloc, .{
            .sel = .init(screen.pages.getTopLeft(.screen), screen.pages.getBottomRight(.screen).?, false),
            .trim = false,
        });
        defer alloc.free(whole);
        const utf16 = try std.unicode.utf8ToUtf16LeAlloc(alloc, whole);
        defer alloc.free(utf16);
        const range = try selectionUtf16Range(screen, selection);
        try testing.expectEqual(@as(usize, 8), range.location);
        try testing.expectEqualSlices(u16, &.{ 's', 'a', 'm', 'e' }, utf16[range.location..][0..range.length]);
    }
}

test "StringMap owned text selection snapshot" {
    const testing = std.testing;
    const alloc = testing.allocator;
    const Terminal = @import("Terminal.zig");
    const Failure = struct {
        fn run(failing: Allocator, s: *Screen) !void {
            const snapshot = try textSnapshot(s, failing);
            defer snapshot.deinit(failing);
        }
    };
    var t = try Terminal.init(testing.io, alloc, .{ .cols = 10, .rows = 3 });
    defer t.deinit(alloc);
    var stream = t.vtStream();
    defer stream.deinit();
    stream.nextSlice("abcde\r\nfghij");
    const screen = t.screens.active;
    const unselected = try textSnapshot(screen, alloc);
    defer unselected.deinit(alloc);
    try testing.expectEqualStrings("abcde\nfghij", unselected.text);
    try testing.expectEqualStrings("", unselected.selected_text);
    try testing.expectEqual(@as(usize, 0), unselected.ranges.len);
    const start = screen.pages.pin(.{ .screen = .{ .x = 1, .y = 0 } }).?;
    const end = screen.pages.pin(.{ .screen = .{ .x = 2, .y = 1 } }).?;
    try screen.select(.init(start, end, true));
    const rectangle = try textSnapshot(screen, alloc);
    defer rectangle.deinit(alloc);
    try testing.expectEqualStrings("bc\ngh", rectangle.selected_text);
    try testing.expectEqualSlices(Utf16Range, &.{
        .{ .location = 1, .length = 2 },
        .{ .location = 7, .length = 2 },
    }, rectangle.ranges);
    try testing.checkAllAllocationFailures(alloc, Failure.run, .{screen});
    try screen.select(.init(start, end, false));
    const contiguous = try textSnapshot(screen, alloc);
    defer contiguous.deinit(alloc);
    try testing.expectEqualStrings("bcde\nfgh", contiguous.selected_text);
    try testing.expectEqualSlices(Utf16Range, &.{.{ .location = 1, .length = 8 }}, contiguous.ranges);
    try testing.checkAllAllocationFailures(alloc, Failure.run, .{screen});
    stream.nextSlice("\x1b[2J\x1b[Hchanged");
    try testing.expectEqualStrings("abcde\nfghij", rectangle.text);
    try testing.expectEqualStrings("bc\ngh", rectangle.selected_text);
    try testing.expectEqualStrings("bcde\nfgh", contiguous.selected_text);

    // Check ownership cleanup at every allocation boundary, with and without
    // selection. No app/CoreFoundation mock can detect these core leaks.
    try testing.checkAllAllocationFailures(alloc, Failure.run, .{screen});
    screen.clearSelection();
    try testing.checkAllAllocationFailures(alloc, Failure.run, .{screen});
}

test "StringMap rectangle snapshot scaling" {
    const testing = std.testing;
    const alloc = testing.allocator;
    const Terminal = @import("Terminal.zig");
    for ([_]u16{ 128, 512, 2048 }) |rows| {
        var t = try Terminal.init(testing.io, alloc, .{ .cols = 80, .rows = rows });
        defer t.deinit(alloc);
        var stream = t.vtStream();
        defer stream.deinit();
        for (0..rows) |y| {
            if (y > 0) stream.nextSlice("\r\n");
            stream.nextSlice("abcdefghijklmnopqrstuvwxyz0123456789");
        }
        const screen = t.screens.active;
        try screen.select(.init(
            screen.pages.pin(.{ .screen = .{ .x = 2, .y = 0 } }).?,
            screen.pages.pin(.{ .screen = .{ .x = 8, .y = rows - 1 } }).?,
            true,
        ));
        const start = std.Io.Timestamp.now(testing.io, .awake);
        const snapshot = try textSnapshot(screen, alloc);
        defer snapshot.deinit(alloc);
        const elapsed = start.durationTo(std.Io.Timestamp.now(testing.io, .awake)).toNanoseconds();
        try testing.expectEqual(@as(usize, rows), snapshot.ranges.len);
        for (snapshot.ranges, 0..) |range, y| {
            try testing.expectEqual(@as(usize, y * 37 + 2), range.location);
            try testing.expectEqual(@as(usize, 7), range.length);
        }
        // Keep the original prefix-per-row algorithm as a correctness and
        // timing control. Diagnostic only: wall-clock thresholds flake in CI.
        const reference_start = std.Io.Timestamp.now(testing.io, .awake);
        for (snapshot.ranges, 0..) |range, y| {
            const a = screen.pages.pin(.{ .screen = .{ .x = 2, .y = @intCast(y) } }).?;
            const b = screen.pages.pin(.{ .screen = .{ .x = 8, .y = @intCast(y) } }).?;
            try testing.expectEqual(range, try selectionUtf16Range(screen, .init(a, b, true)));
        }
        const reference_elapsed = reference_start.durationTo(std.Io.Timestamp.now(testing.io, .awake)).toNanoseconds();
        std.debug.print("snapshot rows={d} elapsed_ns={d} reference_ns={d}\n", .{ rows, elapsed, reference_elapsed });
    }
}

test "StringMap rectangle snapshot across page boundaries" {
    const testing = std.testing;
    const alloc = testing.allocator;
    const Terminal = @import("Terminal.zig");
    var t = try Terminal.init(testing.io, alloc, .{ .cols = 80, .rows = 2, .max_scrollback_bytes = null });
    defer t.deinit(alloc);
    var stream = t.vtStream();
    defer stream.deinit();
    // Include deferred blank rows, explicit spaces and a wrapped wide glyph.
    // Scrollback crosses multiple pages with distinct formatting state.
    for (0..300) |_| stream.nextSlice("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" ++ "\u{1f680}e\u{301}\r\n\r\n  xyz\r\n");
    const screen = t.screens.active;
    const bottom = screen.pages.getBottomRight(.screen).?;
    const last_y = screen.pages.pointFromPin(.screen, bottom).?.screen.y;
    try testing.expect(screen.pages.getTopLeft(.screen).node != bottom.node);
    for ([_]usize{ 0, last_y / 2, last_y - 3 }) |first_y| {
        for ([_][2]u16{ .{ 0, 0 }, .{ 1, 3 }, .{ 76, 79 } }) |columns| {
            const top = screen.pages.pin(.{ .screen = .{ .x = columns[0], .y = @intCast(first_y) } }).?;
            var end = bottom;
            end.x = columns[1];
            try screen.select(.init(top, end, true));
            const snapshot = try textSnapshot(screen, alloc);
            defer snapshot.deinit(alloc);
            const whole = try std.unicode.utf8ToUtf16LeAlloc(alloc, snapshot.text);
            defer alloc.free(whole);
            var rows = top.rowIterator(.right_down, bottom);
            var index: usize = 0;
            while (rows.next()) |row| {
                var a = row;
                a.x = columns[0];
                var b = row;
                b.x = columns[1];
                const selection = Selection.init(a, b, true);
                const expected = try selectionUtf16Range(screen, selection);
                if (expected.length == 0) continue;
                try testing.expectEqual(expected, snapshot.ranges[index]);
                const text = try screen.selectionString(alloc, .{ .sel = selection, .trim = false });
                defer alloc.free(text);
                const utf16 = try std.unicode.utf8ToUtf16LeAlloc(alloc, text);
                defer alloc.free(utf16);
                try testing.expectEqualSlices(u16, utf16, whole[expected.location..][0..expected.length]);
                index += 1;
            }
            try testing.expectEqual(index, snapshot.ranges.len);
        }
    }
}

/// Resolve an AX range only against the exact text the caller observed. A
/// terminal cell cannot represent half a surrogate pair or combining sequence;
/// reject ranges which do not round-trip rather than silently selecting more.
/// The returned pins are borrowed; keep the screen locked until applied.
pub fn selectionForRange(
    screen: *Screen,
    alloc: Allocator,
    expected_text: []const u8,
    range: Utf16Range,
) !?Selection {
    const bottom = screen.pages.getBottomRight(.screen) orelse return error.InvalidRange;
    const map = try screen.selectionStringMap(alloc, .{
        .sel = .init(screen.pages.getTopLeft(.screen), bottom, false),
        .trim = false,
    });
    defer map.deinit(alloc);
    if (!std.mem.eql(u8, expected_text, map.string)) return error.StaleText;
    const end = std.math.add(usize, range.location, range.length) catch return error.InvalidRange;
    var offset: usize = 0;
    var units: usize = 0;
    var start_byte: ?usize = null;
    var end_byte: ?usize = null;
    while (true) {
        if (units == range.location) start_byte = offset;
        if (units == end) end_byte = offset;
        if (offset == map.string.len) break;
        const length = try std.unicode.utf8ByteSequenceLength(map.string[offset]);
        units += if (length == 4) @as(usize, 2) else 1;
        offset += length;
    }
    const start = start_byte orelse return error.InvalidRange;
    const finish = end_byte orelse return error.InvalidRange;
    if (range.length == 0) return null;
    const a = map.map.get(start) orelse return error.InvalidRange;
    const b = map.map.get(finish - 1) orelse return error.InvalidRange;
    const selection: Selection = .init(a, b, false);
    const actual = try selectionUtf16Range(screen, selection);
    if (actual.location != range.location or actual.length != range.length) return error.InvalidRange;
    return selection;
}

test "AccessibilityText write range validates stale text and cell boundaries" {
    const testing = std.testing;
    const alloc = testing.allocator;
    var t = try @import("Terminal.zig").init(testing.io, alloc, .{ .cols = 30, .rows = 5 });
    defer t.deinit(alloc);
    var stream = t.vtStream();
    defer stream.deinit();
    stream.nextSlice("same same \u{1f680}e\u{301}\r\nlast");
    const screen = t.screens.active;
    const snapshot = try textSnapshot(screen, alloc);
    defer snapshot.deinit(alloc);
    for ([_]Utf16Range{ .{ .location = 5, .length = 4 }, .{ .location = 10, .length = 4 }, .{ .location = 15, .length = 4 } }) |range| {
        const selection = (try selectionForRange(screen, alloc, snapshot.text, range)).?;
        try screen.select(selection);
        const actual = try textSnapshot(screen, alloc);
        defer actual.deinit(alloc);
        try testing.expectEqual(range, actual.ranges[0]);
    }
    try testing.expectError(error.InvalidRange, selectionForRange(screen, alloc, snapshot.text, .{ .location = 11, .length = 1 }));
    try testing.expectError(error.InvalidRange, selectionForRange(screen, alloc, snapshot.text, .{ .location = 12, .length = 1 }));
    try testing.expectError(error.InvalidRange, selectionForRange(screen, alloc, snapshot.text, .{ .location = 10000, .length = 1 }));
    try testing.expectEqual(@as(?Selection, null), try selectionForRange(screen, alloc, snapshot.text, .{ .location = 0, .length = 0 }));
    stream.nextSlice("new output");
    try testing.expectError(error.StaleText, selectionForRange(screen, alloc, snapshot.text, .{ .location = 5, .length = 4 }));
}
