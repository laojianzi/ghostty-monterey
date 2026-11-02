import Testing

// Build both the public library and its compiler plugin without Ghostty fixtures.
@Test func dependencyMacroExpansion() {
    #expect(1 + 1 == 2)
}
