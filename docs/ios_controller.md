# iOS Controller and Live Activity Implementation Notes

This checkout does not contain the PhoneAgent SwiftUI app, XCTest bundle, or Widget
Extension sources. The intended iOS changes should be applied inside the actual
PhoneAgent Xcode project without replacing the existing XCTest bridge.

## Controller UI defaults

- Black Siri-style SwiftUI surface with white text and blue accent glow.
- Always-visible Pause/Stop button while a session is armed or running.
- Settings for gateway URL, Keychain-stored bearer token, model mode, low-context
  mode, screenshot policy, latency profile, natural-break voice interjection, and strict approval policy.
- Approval cards should show app, target, action, reason, risk, Approve, and Deny.
- Use native SwiftUI materials and respect Reduce Motion.

## Natural-break microphone portal

When the gateway creates an interjection, the iPhone controller should open a
short-lived microphone session, detect whether anyone is talking, wait for a
natural silence break, speak/show the agent question, then close the microphone
session. Use on-device Speech/VAD when possible; do not stream audio to cloud STT
without an explicit user opt-in. Defaults: 45 second maximum listen window and
900 ms silence threshold. Show a visible mic indicator and cancellation control.

## Low-latency toggles

Expose these settings with one-line trade-off explanations:

- Prefetch accessibility tree: faster decisions, small local bridge cost.
- Auto screenshot thumbnail: faster visual grounding, more battery/privacy cost.
- Prewarm local model: faster first token, keeps local model active.
- Optimistic low-risk clicks: fastest navigation, less conservative verification.
- Observe after action: safer recovery, adds latency.

## Deep links

Register these URL patterns in the app target:

- `phoneagent://request`
- `phoneagent://session/{id}`
- `phoneagent://approve/{id}`

## Live Activity / Dynamic Island

Implement a Widget Extension with ActivityKit. The activity should start only
when the user arms or starts a PhoneAgent session and should end when idle,
stopped, or complete. Do not represent this as a permanent Dynamic Island
resident.

Recommended attributes:

```swift
struct PhoneAgentActivityAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var status: String
        var taskTitle: String
        var sessionID: String?
        var awaitingApproval: Bool
    }

    var controllerName: String
}
```

Use a black compact pill, white text, and a subtle blue glow. If interactive Live
Activity buttons are not available for the minimum supported iOS version, use
`Link`/deep-link controls that open the app to the request, session, or approval
screen.
