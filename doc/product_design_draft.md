classDiagram
    class PullRequest {
        +String title
        +String intentDescription
        +Status status
    }
    class Artifact {
        +Type type (Code/Diagram)
        +String content
    }
    class Agent {
        +Role role
        +evaluate(Artifact, Intent)
    }
    class Feedback {
        +String comment
        +Severity severity
        +bool isResolved
    }

    PullRequest "1" *-- "many" Artifact
    PullRequest "1" --> "many" Feedback
    Agent "many" ..> "1" PullRequest : reviews
    Agent "1" --> "many" Feedback : creates
    Orchestrator --|> Agent : manages others