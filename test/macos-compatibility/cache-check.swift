import Foundation

@main
struct CacheChecks {
    final class Token {}

    static func main() throws {
        var calls = 0
        let cache = CachedValue<Int>(duration: .milliseconds(20)) {
            calls += 1
            return calls
        }
        precondition(cache.get() == 1 && cache.get() == 1)
        Thread.sleep(forTimeInterval: 0.04)
        precondition(cache.get() == 2)

        // Even when asynchronous eviction has not run, a zero-duration value
        // must not be returned again. The callback of an older generation must
        // not clear a newer value.
        let immediate = CachedValue<Int>(duration: .seconds(0)) {
            calls += 1
            return calls
        }
        let initial = immediate.get()
        precondition(immediate.get() == initial + 1)

        // Explicit invalidation must discard the old value without allowing a
        // cancelled eviction callback to clear the replacement generation.
        let invalidated = CachedValue<Int>(duration: .seconds(60)) {
            calls += 1
            return calls
        }
        let beforeInvalidation = invalidated.get()
        invalidated.invalidate()
        precondition(invalidated.get() == beforeInvalidation + 1)
        Thread.sleep(forTimeInterval: 0.04)
        precondition(invalidated.get() == beforeInvalidation + 1)

        var sharedCalls = 0
        let shared = CachedValue<Int>(duration: .seconds(60)) {
            sharedCalls += 1
            return sharedCalls
        }
        DispatchQueue.concurrentPerform(iterations: 1000) { _ in
            precondition(shared.get() == 1)
        }
        precondition(sharedCalls == 1)

        Thread.sleep(forTimeInterval: 0.04)
        precondition(shared.get() == 1 && sharedCalls == 1)

        // Idle caches must release their payload, not just refetch lazily.
        let expiring = CachedValue<Token>(duration: .milliseconds(5)) { Token() }
        weak var token = expiring.get()
        let deadline = Date().addingTimeInterval(5)
        while token != nil && Date() < deadline { Thread.sleep(forTimeInterval: 0.005) }
        precondition(token == nil)

        var disposable: CachedValue<Token>? = CachedValue(duration: .seconds(60)) { Token() }
        weak var payload = disposable!.get()
        weak var owner = disposable
        disposable = nil
        precondition(owner == nil && payload == nil)
        print("Cache reuse, expiry, concurrency, and lifetime checks passed")
    }
}
