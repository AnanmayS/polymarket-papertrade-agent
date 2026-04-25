# Architecture

```mermaid
flowchart LR
    A[Polymarket Gamma API] --> B[Scanner Service]
    B --> C[(Market + Snapshot Tables)]
    C --> D[Signal Service]
    D --> E[Probability Model Service]
    E --> F[Risk Service]
    F --> G[Paper Execution Service]
    G --> H[(Trades + Positions)]
    H --> I[Settlement Service]
    I --> J[(Postmortems + Portfolio Snapshots)]
    C --> K[FastAPI Routes]
    H --> K
    J --> K
    K --> L[React Dashboard]
```

The MVP is intentionally paper-trading only. The execution boundary is isolated behind `PaperExecutionService`, which makes it straightforward to add a real execution adapter later without rewriting the scanner, signal engine, or risk layer.

