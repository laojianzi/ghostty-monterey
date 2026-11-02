#import <AppKit/AppKit.h>
#include <errno.h>
#include <pthread.h>
#include <time.h>

// A native control, deliberately independent of Ghostty and its undo manager.
static double uptime(void) {
    return NSProcessInfo.processInfo.systemUptime;
}

static void *sleepWorker(void *context) {
    double start = uptime();
    struct timespec requested = {0, 10000000};
    int result = nanosleep(&requested, NULL);
    int error = result == 0 ? 0 : errno;
    printf("worker_sleep_ms=%.3f result=%d errno=%d\n",
           (uptime() - start) * 1000, result, error);
    fflush(stdout);
    return NULL;
}

@interface SchedulingProbe : NSObject <NSApplicationDelegate>
@property(strong) id activity;
@property(strong) NSWindow *window;
@property(strong) NSTimer *idleTimer;
@property(strong) NSTimer *expiryTimer;
@end

@implementation SchedulingProbe
- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    if (getenv("GHOSTTY_SCHEDULING_PROBE_ACTIVITY")) {
        self.activity = [NSProcessInfo.processInfo
            beginActivityWithOptions:NSActivityUserInitiated
                              reason:@"Isolated scheduling diagnostic"];
    }
    self.window = [[NSWindow alloc]
        initWithContentRect:NSMakeRect(100, 100, 800, 500)
                  styleMask:(NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                             NSWindowStyleMaskResizable)
                    backing:NSBackingStoreBuffered
                      defer:NO];
    [self.window orderFront:nil];
    double start = uptime();
    printf("start=%.3f activity=%d\n", start, self.activity != nil);
    fflush(stdout);

    self.idleTimer = [NSTimer scheduledTimerWithTimeInterval:35 repeats:NO block:^(NSTimer *timer) {
        double closed = uptime();
        printf("idle_elapsed=%.3f\n", closed - start);
        fflush(stdout);
        self.expiryTimer = [NSTimer scheduledTimerWithTimeInterval:5 repeats:NO block:^(NSTimer *timer) {
            printf("expiry_elapsed=%.3f\n", uptime() - closed);
            fflush(stdout);
            pthread_t worker;
            int result = pthread_create(&worker, NULL, sleepWorker, NULL);
            if (result != 0) {
                fprintf(stderr, "pthread_create: %d\n", result);
                exit(1);
            }
            result = pthread_join(worker, NULL);
            if (result != 0) {
                fprintf(stderr, "pthread_join: %d\n", result);
                exit(1);
            }
            if (self.activity) [NSProcessInfo.processInfo endActivity:self.activity];
            [NSApp terminate:nil];
        }];
    }];
}
@end

int main(void) {
    @autoreleasepool {
        NSApplication *app = NSApplication.sharedApplication;
        SchedulingProbe *delegate = [SchedulingProbe new];
        app.delegate = delegate;
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        [app run];
    }
    return 0;
}
