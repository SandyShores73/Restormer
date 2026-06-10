# iOS Controller and Live Activity Implementation Notes

This checkout does not contain the PhoneAgent SwiftUI app, XCTest bundle, or Widget
Extension sources. The intended iOS changes should be applied inside the actual
PhoneAgent Xcode project without replacing the existing XCTest bridge.

## Controller UI defaults

- Black Siri-style SwiftUI surface with white text and blue accent glow.
- Always-visible Pause/Stop button while a session is armed or running.
- Settings for gateway URL, Keychain-stored bearer token, model mode, low-context
  mode, screenshot policy, and strict approval policy.
- Approval cards should show app, target, action, reason, risk, Approve, and Deny.
- Use native SwiftUI materials and respect Reduce Motion.

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
