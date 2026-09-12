Yes. Given the latest clarification, I would make **Processing Window + Prefund Request/Transaction + $ Value + Settlement Outcome** the core of both dashboards.

Below is a **full widget catalog** rather than a final dashboard. I’ve intentionally included more options than should fit on one screen so you can select the best set.

> **Important:** File count is now a secondary/diagnostic metric because production normally has ~1 file per window. The primary dimensions are **requests, transactions, amount, status, latency, and exceptions**.

---

# 1. Common Dashboard Data Model

Every widget should be filterable by:

| Field                         | Example                                           |
| ----------------------------- | ------------------------------------------------- |
| Business Date                 | 2026-09-12                                        |
| Processing Window ID          | PW-20260912-1000                                  |
| Window Start                  | 10:00                                             |
| Window End                    | 11:00                                             |
| Window Duration               | 60 min                                            |
| Processing Type               | PREFUND / SETTLEMENT                              |
| Business Date/Settlement Date | 2026-09-12                                        |
| Status                        | ON_TRACK / AT_RISK / DELAYED / FAILED / COMPLETED |

For testing, the window simply becomes:

```text
5 minutes / 10 minutes
```

instead of:

```text
60 minutes
```

---

# 2. Dashboard A — Operations / Business

## Purpose

The Operations/Business dashboard should answer:

> **How much business entered the platform during each processing window, how many transactions were processed, how much money was reserved/settled, and are we on track?**

I would organize the widgets into:

1. Current Window
2. Window Summary
3. Prefund
4. Fund Reservation
5. Settlement
6. Trends
7. SLA/Performance
8. Exceptions
9. Business Impact
10. Historical comparison

---

# 3. Operations — Current Window KPI Widgets

These are the highest-value widgets.

## O-B01 — Current Window

**Widget:** Status card

| Field               | Description                           |
| ------------------- | ------------------------------------- |
| Window ID           | Unique processing window              |
| Start Time          | Window start                          |
| End Time            | Window end                            |
| Elapsed Time        | Current elapsed time                  |
| Remaining Time      | Remaining window time                 |
| Status              | On Track / At Risk / Delayed / Failed |
| Last Activity       | Latest processing event               |
| Last Updated        | Dashboard refresh                     |

Example:

```text
CURRENT WINDOW
10:00 – 11:00

● ON TRACK

Elapsed: 32 min
Remaining: 28 min
Last activity: 10:31:42
```

---
 

## O-B03 — Transaction Count

**Widget:** KPI card

Fields:
* Window
* Type (Prefund/Settlement)
* Transactions Received
* Transactions Processed
* Transactions Pending
* Transactions Failed
* Completion %

---

## O-B04 — Prefund Requested Value

**Widget:** KPI card

Fields:
* Window
* Transaction Count
* Requested Amount
* Previous Window Amount
* Variance $
* Variance %
* Currency

Example:

```text
PREFUND VALUE
$24.8M
+$3.2M | +14.8%
```

---

## O-B05 — Reserved Value

Fields:

* Reservation Requested $
* Reservation Successful $
* Reservation Pending $
* Reservation Failed $
* Reservation Success %

---

## O-B06 — Settlement Value

Fields:

* Settlement Received $
* Settlement Matched $
* Settlement Completed $
* Settlement Pending $
* Settlement Failed $
* Unmatched $
* Mismatch $

---

# 4. Operations — Current Window Summary Table

## O-B07 — Prefund / Settlement Window Summary

I strongly recommend this table.

| Metric       |  Prefund | Settlement |
| ------------ | -------: | ---------: |
| Transactions |   18,452 |     11,240 |
| Received $   |   $24.8M |     $15.2M |
| Processed $  |   $24.0M |     $15.1M |
| Pending      |      220 |          8 |
| Pending $    |    $0.8M |      $0.1M |
| Failed       |       22 |          0 |
| Failed $     |    $0.0M |         $0 |
| Avg Time     |    420ms |      480ms |
| P95          |    850ms |      920ms |
| Status       | ON TRACK |   ON TRACK |

This is probably the **single best non-chart widget** for your dashboard.

---

# 5. Operations — Prefund Widgets

## O-B08 — Prefund Processing Funnel

**Widget:** Funnel

```text
Transactions Received
        ↓
Validated
        ↓
Reservation Requested
        ↓
Reservation Responded
        ↓
Reserved
        ↓
Completed
```

Fields:

* Count
* $
* Conversion %
* Drop-off count
* Drop-off %

---

## O-B09 — Prefund Status Distribution

**Widget:** Donut/Pie or horizontal bar

Categories:

* Received
* Processing
* Reservation Pending
* Reserved
* Failed
* Retry Pending
* Retry Exhausted

Fields:

* Transaction Count
* Amount $
* Percentage

For operational use, I prefer **horizontal bar** over pie when there are many statuses.

---

## O-B10 — Prefund Request Count Trend

**Widget:** Line

Fields:

* Window
* Request Count
* Transaction Count
* Previous-period baseline, if desired

If Prefund request and transaction are always one-to-one, don't graph both—use **one primary series** and expose the other in the tooltip/KPI.

---

# 6. Operations — Prefund Dollar Trend

## O-B11 — Prefund Value by Window

Fields:

* Requested $
* Reserved $
* Pending $
* Failed $
* Reservation success %

---

# 7. Operations — Fund Reservation Widgets

This deserves a dedicated section.

## O-B12 — Reservation KPI Group

| Field                |
| -------------------- |
| Reservation Requests |
| Responses Received   |
| Reserved             |
| Pending              |
| Rejected             |
| Timeout              |
| Failed               |
| Retry                |
| Retry Exhausted      |
| Success %            |

---

## O-B13 — Reservation Response Time

Fields:

* Avg
* P50
* P95
* P99
* Max
* Timeout threshold

---

## O-B14 — Reservation Response Time Trend

**Graph:** Line

```text
Window
  ↓
Average
P95
P99
```

This is particularly useful for detecting degradation before transaction failures become significant.

---

## O-B15 — Reservation Retry Trend

Fields:

* Retry #1
* Retry #2
* Retry #3
* Retry exhausted
* Retry rate

---

## O-B16 — Reservation Outcome

**Graph:** Bar/Donut

Categories:

* Reserved
* Pending
* Rejected
* Timeout
* Failed
* Retry Pending
* Retry Exhausted

Show:

**Count + $ Value**

---

# 8. Operations — Settlement Widgets

## O-B17 — Settlement Processing Funnel

```text
Settlement Received
        ↓
Validated
        ↓
Prefund Matched
        ↓
Amount Validated
        ↓
Converted
        ↓
Outbound Generated
        ↓
Sent
        ↓
Completed
```

Fields at each stage:

* Transaction count
* $
* Duration
* Success %
* Failure count

---

## O-B18 — Settlement Transaction Trend

**Graph:** Line

Fields:

* Settlement transactions
* Matched
* Completed
* Pending
* Failed

---

## O-B19 — Settlement Value Trend

**Graph:** Line

Fields:

* Received $
* Matched $
* Settled $
* Pending $
* Unmatched $

---

## O-B20 — Settlement Matching

**Widget:** KPI group

```text
Settlement Transactions       11,240
Matched                       11,228
Unmatched                         12
Match Rate                     99.89%

Settlement Value               $15.2M
Matched Value                  $15.17M
Unmatched Value                   $25K
```

---

## O-B21 — Settlement Exceptions

Fields:

* Unmatched count
* Unmatched $
* Amount mismatch count
* Amount mismatch $
* Duplicate settlement
* Missing Prefund
* Invalid settlement
* Conversion failure
* Outbound failure

---

# 9. Operations — Processing Performance

## O-B22 — End-to-End Processing Time

Metrics:

* Avg
* P50
* P95
* P99
* Max

Break down:

```text
Prefund
Reservation
Settlement
End-to-End
```

---

## O-B23 — Processing Time Trend

**Graph:** Line

---

# 10. Operations — SLA Widgets

## O-B24 — Window SLA Status

Fields:

* Expected completion
* Actual completion
* SLA threshold
* Remaining time
* Variance
* Status

Statuses:

```text
ON TRACK
AT RISK
DELAYED
FAILED
COMPLETED
```

---

## O-B25 — SLA Compliance Trend

Fields:

* Windows processed
* Windows within SLA
* Windows outside SLA
* SLA %
* Average delay
* Maximum delay

---

# 11. Operations — Pending / Business Impact

## O-B26 — Pending Transactions

Fields:

* Pending Prefund
* Pending Settlement
* Pending Reservation
* Total

---

## O-B27 — Pending Value

Fields:

* Prefund Pending $
* Reservation Pending $
* Settlement Pending $
* Total Pending $

---

## O-B28 — Amount at Risk

```text
Failed $
+
Pending $
+
Unmatched $
+
Mismatch $
=
Business Amount at Risk
```

This should be a **major KPI**.

---

# 12. Operations — Failure Widgets

## O-B29 — Failure Summary

```text
                    COUNT       VALUE
Prefund Failed       22         $0.3M
Reservation Failed   18         $0.2M
Settlement Failed     0         $0
Unmatched            12         $25K
Mismatch              2         $8K
```

---

## O-B30 — Failure Trend

Graph by window:

* Failure count
* Failed $
* Failure %

---

## O-B31 — Failure Rate

Fields:

* Failed transactions
* Total transactions
* Failure %
* Previous window failure %
* Variance

---

# 13. Operations — Historical Comparison

## O-B32 — Current vs Previous Window

| Metric                  | Current | Previous | Change |
| ----------------------- | ------: | -------: | -----: |
| Prefund Transactions    |  18,452 |   17,210 |  +7.2% |
| Prefund $               |  $24.8M |   $22.1M | +12.2% |
| Reservation Success     |   98.8% |    99.1% |  -0.3% |
| Settlement Transactions |  11,240 |   10,980 |  +2.4% |
| Settlement $            |  $15.2M |   $14.8M |  +2.7% |
| P95                     |   850ms |    710ms | +19.7% |

This is extremely useful for Business Operations.

---

# 14. Operations — Volume vs Value

## O-B33 — Transaction Volume Trend

Shows transaction count.

## O-B34 — Dollar Value Trend

Shows $.

## O-B35 — Average Transaction Value

Formula:

```text
Total Transaction Amount
÷
Transaction Count
```

This can reveal:

> Transaction volume is normal, but average transaction size is increasing.

---

# 15. Operations — Business Mix

Potential widgets if there are meaningful business dimensions.

### O-B36 — Transactions by Business Type

Fields:

* Business Type
* Transaction Count
* $
* % of total

### O-B37 — Value by Business Type

Horizontal bar.

### O-B38 — Transactions by Origin/Source

Fields:

* Source
* Count
* $
* Failure %
* Processing time

Only add these if those dimensions are genuinely useful to your business.

---

# 16. Support Dashboard

Support should be much more diagnostic.

The question changes to:

> **Which window is abnormal, what transaction/value is affected, where did processing stop, what caused it, and what can I do?**

---

# 17. Support — Top KPI Widgets

## S01 — Windows Requiring Attention

Fields:

* At Risk
* Delayed
* Failed
* Reconciliation Required

---

## S02 — Pending Reservations

Fields:

* Count
* $
* Oldest age
* Average age
* P95 age

---

## S03 — Reservation Timeouts

Fields:

* Count
* $
* Current window
* Previous window
* Timeout rate

---

## S04 — Retry Exhausted

Fields:

* Count
* $
* Processing type
* Error code

---

## S05 — Failed Transactions

Fields:

* Count
* $
* Prefund
* Reservation
* Settlement

---

## S06 — Reconciliation Required

Fields:

* Count
* $
* Prefund
* Settlement
* Reason

---

# 18. Support — Window Exception Queue

## S07 — Windows Requiring Attention

This should probably be the **primary Support widget**.

| Window | Type       | Status  | Transactions |     $ | Issue               | Age | Action    |
| ------ | ---------- | ------- | -----------: | ----: | ------------------- | --: | --------- |
| 10:00  | Prefund    | AT RISK |          220 | $0.8M | Reservation timeout |  4m | Retry     |
| 09:00  | Settlement | DELAYED |           12 |  $25K | Unmatched           | 18m | Reconcile |
| 08:00  | Prefund    | FAILED  |           42 | $0.3M | Validation          | 32m | Review    |

Fields:

* Window ID
* Processing Type
* Status
* Transaction Count
* Amount
* Error Code
* Error Count
* Oldest Age
* Root Cause
* Retryable
* Recovery Action
* Assigned To

---

# 19. Support — Prefund Exceptions

## S08 — Prefund Exception Breakdown

Categories:

* Validation failure
* Duplicate
* Parsing
* Persistence
* Reservation timeout
* Reservation rejection
* Reservation failure
* Retry exhausted

Each:

**Count + $ + affected window**

---

# 20. Support — Settlement Exceptions

## S09 — Settlement Exception Breakdown

Categories:

* Prefund not found
* Unmatched transaction
* Amount mismatch
* Duplicate
* Invalid transaction
* Conversion failure
* Outbound generation failure
* Outbound delivery failure

---

# 21. Support — Response Time Anomaly

## S10 — Response Time by Window

| Window | Prefund P95 | Reservation P95 | Settlement P95 | Status |
| ------ | ----------: | --------------: | -------------: | ------ |
| 08:00  |       850ms |           700ms |          920ms | 🟢     |
| 08:10  |       920ms |           810ms |           1.1s | 🟢     |
| 08:20  |       1.25s |            1.3s |           1.5s | 🟡     |
| 08:30  |        4.2s |            5.1s |           4.8s | 🔴     |

Support should be able to click a row and see the stage responsible.

---

# 22. Support — Processing Bottleneck

## S11 — Stage Response Time

```text
Prefund
────────────────────────────
Validation             42ms
Persistence             80ms
MQ Publish              25ms
Reservation Response   820ms  ←
DB Update               40ms

Settlement
────────────────────────────
Validation              35ms
Matching                65ms
Conversion              90ms
Outbound Generation    320ms
Delivery                 45ms
```

Fields:

* Stage
* Avg
* P95
* P99
* Max
* Error count
* Timeout count

---

# 23. Support — Pending Aging

## S12 — Pending Transaction Aging

Buckets:

```text
< 30 sec
30 sec – 1 min
1 – 5 min
5 – 10 min
10 – 30 min
30 – 60 min
> 60 min
```

For each:

* Transaction count
* $
* Prefund
* Settlement
* Reservation

---

# 24. Support — Error Trend

## S13 — Error Trend by Window

Fields:

* Window
* Error Code
* Count
* $
* Processing Type

---

# 25. Support — Top Error Codes

## S14 — Error Ranking

| Error Code | Count | $ Impact | Type       | Retryable | Current State |
| ---------- | ----: | -------: | ---------- | --------- | ------------- |
| MQ-001     |    42 |    $2.1M | Prefund    | Yes       | Retrying      |
| SETTLE-002 |    18 |    $0.8M | Settlement | No        | Review        |
| FILE-004   |     7 |    $0.3M | Prefund    | No        | Failed        |

---

# 26. Support — Recovery Queue

## S15 — Recovery Actions

This is a very valuable widget.

Categories:

* Retry pending
* Retry exhausted
* Reprocess required
* Reconciliation required
* Manual review
* Awaiting dependency
* Awaiting Prefund
* Awaiting Settlement

Fields:

* Item ID
* Window
* Type
* Transaction count
* $
* Error
* Retry count
* Next action
* Action owner
* Age

---

# 27. Support — Fund Reservation Diagnostics

## S16 — Reservation Health

```text
Requests              18,452
Responses             18,230
Pending                  220
Timeouts                  18
Retries                  142
Exhausted                  7

Avg Response             420ms
P95                       850ms
P99                     1.4sec
```

---

# 28. Support — MQ Diagnostic Widget

Keep this **secondary**, because MQ is the mechanism rather than the business outcome.

## S17 — MQ Health

Fields:

* Connection status
* Request messages
* Response messages
* Publish failures
* Receive failures
* Timeout count
* Retry count
* Unprocessed messages
* Consumer lag
* Connection reconnects
* Request/response correlation failures

The key distinction:

**Business dashboard:**

> 220 reservations pending.

**Support dashboard:**

> 220 reservations pending because 18 requests timed out and MQ response latency P95 increased to 5.1 seconds.

---

# 29. Support — Transaction Drill-Down

## S18 — Transaction Timeline

Common model for Prefund and Settlement:

```text
Transaction
     │
     ├── Window
     ├── Amount
     ├── Current Status
     │
     ▼
Processing Timeline
     │
     ├── Received
     ├── Validated
     ├── Persisted
     ├── Reservation Requested
     ├── MQ Published
     ├── Reservation Response
     ├── Settlement Received
     ├── Matched
     ├── Converted
     ├── Sent
     └── Completed
```

Each event should expose:

| Field          |
| -------------- |
| Event ID       |
| Timestamp      |
| Duration       |
| Component      |
| Operation      |
| Status         |
| Correlation ID |
| Message ID     |
| Error Code     |
| Retry Attempt  |
| Data Center    |

---

# 30. Support — Transaction Detail

## S19 — Transaction Detail Card

```text
Transaction ID: TX-12345
Processing Type: PREFUND
Window: 10:00–11:00
Amount: $125,000

Status: RESERVATION_PENDING

Created: 10:01:02
Age: 4m 32s

Reservation:
Request Sent      ✓
MQ Accepted       ✓
Response          ⚠ Pending
Retry Count       1

Business Impact:
$125,000 Pending
```

---

# 31. Support — File Detail

Although files aren't the main dashboard dimension, Support absolutely needs them.

## S20 — File Processing Detail

Fields:

* File ID
* File Name
* File Type
* Window ID
* Received Timestamp
* File Size
* Checksum
* Transaction Count
* Total Amount
* Validation Status
* Processing Status
* Completed Timestamp
* Processing Duration
* Error Code
* Retry Count

---

# 32. Support — Batch Detail

## S21 — Batch Summary

Fields:

* Batch ID
* File ID
* Batch Type
* Transaction Count
* Total Amount
* Processed Count
* Pending Count
* Failed Count
* Processing Duration
* Error count

---

# 33. Support — Data Center Comparison,
Build metadata in audit table based on event and processing type and store include additional required to make the data useful.

## S22 — DC Operational Comparison ,

| Metric           |   DC1 |   DC2 |  % Diff | CN Avg Processing time | PI Avg Processing time
| ---------------- | ----: | ----: |
| Prefund Files    | 9,200 | 9,252 |
| BCBS Requests    |    80 |   140 |
| BCBS Responses   | 999   | 888   |
| Settlement Files | 800   |  1    |
| OMNI Publishing  |     4 |    18 |
and etc , only by processing/event type and core .

Useful for identifying a **DC-specific degradation**.

---

# 34. Support — Correlation Investigation

## S23 — Request/Response Correlation

For Fund Reservation:

```text
Prefund Transaction
       ↓
Reservation Request ID
       ↓
MQ Message ID
       ↓
Reservation Service
       ↓
MQ Response Message ID
       ↓
Reservation Response
       ↓
Transaction Update
```

Fields:

* Transaction ID
* Reservation Request ID
* MQ Message ID
* Correlation ID
* Response Message ID
* Request timestamp
* Response timestamp
* Duration
* Retry count
* Final status

This is extremely useful when investigating "request sent but response not received."

---

# 35. Support — Infrastructure Correlation

## S24 — Dependency Health

Secondary widget.

Track:

* Database
* MQ
* Kafka, if used
* NFS/S3
* External service
* API
* Pod/application

Fields:

* Availability
* Error rate
* Latency
* Connection failures
* Timeout
* Last successful operation

---

# 36. Recommended graph catalog

Here is the **complete graph shortlist** I would consider.

| ID  | Graph                                   | Primary Data         |
| --- | --------------------------------------- | -------------------- |
| G01 | Prefund request count by window         | Request count        |
| G02 | Prefund transaction count by window     | Transaction count    |
| G03 | Prefund $ value by window               | Requested/Reserved $ |
| G04 | Settlement transaction count by window  | Transactions         |
| G05 | Settlement $ value by window            | Settlement $         |
| G06 | Prefund vs Settlement transaction trend | Count                |
| G07 | Prefund vs Settlement $ trend           | $                    |
| G08 | Reservation response time               | Avg/P95/P99          |
| G09 | Prefund processing time                 | Avg/P95/P99          |
| G10 | Settlement processing time              | Avg/P95/P99          |
| G11 | End-to-end processing time              | Avg/P95/P99          |
| G12 | Pending transaction trend               | Count                |
| G13 | Pending $ trend                         | $                    |
| G14 | Failure count trend                     | Count                |
| G15 | Failed $ trend                          | $                    |
| G16 | Reservation retry trend                 | Retry count          |
| G17 | Reservation timeout trend               | Timeout count        |
| G18 | Settlement unmatched trend              | Count/$              |
| G19 | Settlement mismatch trend               | Count/$              |
| G20 | SLA compliance trend                    | %                    |
| G21 | Processing throughput                   | Tx/sec or tx/window  |
| G22 | Processing backlog                      | Count                |
| G23 | Pending aging                           | Count/$              |
| G24 | Error-code trend                        | Error count          |
| G25 | Stage latency                           | Stage duration       |
| G26 | DC comparison                           | Count/latency        |
| G27 | Current vs previous window              | Variance             |
| G28 | Average transaction value               | $/transaction        |
| G29 | Business-type distribution              | Count/$              |
| G30 | Failure-rate trend                      | %                    |

---

# 37. My recommended final selection

You have enough potential widgets here for a very crowded dashboard. I would **not use all of them**.

### Operations / Business — MVP

**Top KPI row**

1. **Current Window Status**
2. **Prefund Requests**
3. **Prefund Transactions**
4. **Prefund $ Value**
5. **Reserved $**
6. **Pending $**
7. **Settlement Transactions**
8. **Settlement $**
9. **Failed $**
10. **Amount at Risk**

**Graphs**

11. **Prefund Transaction/Request Trend**
12. **Prefund $ Value Trend**
13. **Settlement Transaction Trend**
14. **Settlement $ Value Trend**
15. **Processing Response Time — Avg/P95/P99**
16. **Pending $ Trend**
17. **Failure Count/$ Trend**
18. **Prefund → Reservation → Settlement Lifecycle**

**Operational widgets**

19. **Prefund / Settlement Window Summary**
20. **Window SLA / Health**
21. **Fund Reservation Health**
22. **Settlement Matching**

---

# 38. Support — MVP

### KPI row

1. **Windows At Risk**
2. **Pending Reservations**
3. **Pending $**
4. **Failed Transactions**
5. **Failed $**
6. **Reservation Timeouts**
7. **Retry Exhausted**
8. **Reconciliation Required**

### Main widgets

9. **Windows Requiring Attention**
10. **Prefund Exceptions**
11. **Settlement Exceptions**
12. **Pending Aging**
13. **Response-Time Anomalies**
14. **Stage Bottleneck**
15. **Error Trend**
16. **Top Error Codes**
17. **Recovery Queue**
18. **Reservation Diagnostics**
19. **DC Comparison**
20. **MQ Diagnostics**

### Drill-down

21. **Window → File → Batch → Transaction**
22. **Transaction Timeline**
23. **Error Detail**
24. **Root Cause**
25. **Recovery Action**
26. **Request/Response Correlation**

---

# 39. The most important design change

I would now define your dashboard hierarchy as:

```text
                     PROCESSING WINDOW
                            │
             ┌──────────────┴──────────────┐
             │                             │
          PREFUND                      SETTLEMENT
             │                             │
       Requests                       Transactions
       Transactions                   Settlement $
       Prefund $                      Matched
       Reserved $                     Unmatched
       Pending $                      Mismatch
       Failed $                       Pending
             │                             │
             └──────────────┬──────────────┘
                            │
                     FUND RESERVATION
                            │
                  Requests / Responses
                  Pending / Reserved
                  Retry / Timeout
                  Avg / P95 / P99
```

And for **every metric**, retain these dimensions:

```text
Window
  + Processing Type
  + Transaction Count
  + Amount $
  + Status
  + Processing Duration
  + Failure Count
  + Failure $
```

Then:

**Operations/Business sees the aggregate.**

**Support sees the exact same aggregate and drills into the underlying record.**

That gives you one consistent operational data model rather than creating separate reporting logic for each dashboard.


Prefund request and transaction trend

Track Prefund workload across processing windows.

window	requests	transactions
08:00	14,200	14,200
08:10	15,800	15,800
08:20	14,900	14,900
08:30	17,600	17,600
08:40	18,200	18,200
08:50	16,900	16,900
09:00	19,200	19,200

Prefund value by processing window

Track requested, reserved, pending, and failed Prefund value.

window	requested	reserved	pending	failed
08:00	18,200,000	17,900,000	300,000	0
08:10	22,400,000	21,800,000	600,000	0
08:20	19,200,000	19,000,000	200,000	0
08:30	28,600,000	27,400,000	1,100,000	100,000
08:40	31,500,000	30,400,000	1,000,000	100,000
08:50	26,700,000	26,100,000	600,000	0
09:00	34,800,000	33,100,000	1,600,000	100,000

Processing latency trend

Track operational latency across processing windows.

window	prefund	reservation	settlement
08:00	420	310	480
08:10	450	330	510
08:20	440	320	490
08:30	520	380	570
08:40	610	420	650
08:50	580	410	620
09:00	720	520	810



# Build Prompt: ACH Prefund & Settlement Processing Engine Dashboard

## 1. System Context

Enrich both Business and operations dashboard suite for an **ACH Prefund and Settlement processing engine**. The engine works as follows:

- An external vendor delivers a **Prefund file** and a **Settlement (posting) file** to the internal system in fixed, recurring **processing windows**.
  - **Production:** one Prefund file and one Settlement file per 60-minute window.
  - **Test/QA:** one Prefund file and one Settlement file per 5–10 minute window.
- On receipt of the Prefund file, the system creates **Prefund transactions/requests** and issues **fund reservation requests** (via MQ) for each one, reserving funds against expected settlement.
- When the Settlement file arrives for the same window, its transactions are **matched against the reserved Prefund transactions**, validated for amount, converted, and pushed downstream (outbound generation/delivery) to complete settlement.
- The **core Prefund/Settlement system of record** holds all file, transaction, reservation, and settlement data and is the single source of truth the dashboards query.

Because production runs one file per window, **file count is not a meaningful business signal** — the operational and business unit of value is the **Prefund/Settlement transaction (request) and its dollar value**, not the number of files. File-level detail still matters, but only as **metadata/drill-down**, not as a headline KPI.

## 2. Goal

Design two purpose-built, role-specific dashboards that share one operational backbone:

1. **Business / Operations Dashboard** — for executives and business operations: "What happened in this window, how much business value moved, and are Prefund and Settlement on track?"
2. **Support Dashboard** — for support/ops engineers: "What is wrong right now, why did it happen, and how do I recover it?"

Both dashboards must work unmodified whether the configured processing window is 10 minutes (test) or 60 minutes (production). **No dashboard logic may hard-code window duration** — window length and window boundaries must be a configuration input.

## 3. Shared Data & Drill-Down Backbone

All widgets in both dashboards are views into one hierarchy:

```
Processing Window
   └── Prefund  /  Settlement            (parallel tracks, always shown separately, never merged)
         └── File                        (metadata only — 1 per window in production)
               └── Batch
                     └── Transaction / Request
                           └── Fund Reservation (request → response → retry → timeout)
                           └── Settlement Match  (matched / unmatched / amount mismatch)
                                 └── Processing Event Timeline
                                       └── Error
                                             └── Root Cause
                                                   └── Recovery Action
```

Key modeling rules:
- **Prefund and Settlement are always separate rows/sections**, never collapsed into one "files processed" number, throughout both dashboards.
- **Fund Reservation** is modeled as its own business capability sitting between Prefund and Settlement, not as generic infrastructure/MQ monitoring.
- **Window status** ( ON TRACK / AT RISK / DELAYED / FAILED / WAITING / COMPLETED ) is computed independently for Prefund, Settlement, and Fund Reservation, then rolled up to an Overall status using the worst relevant condition.
- **File count, files/hour, file watcher status, NFS/S3/MQ connection health, pod count, CPU/memory** are all secondary/technical — surface them only in drill-down or an infrastructure view, never as a primary KPI.

## 4. Global Filters / Header (both dashboards)

| Filter | Type | Notes |
|---|---|---|
| Processing Window | Dropdown, dynamic | Options generated from configured window size (e.g. 10:00–10:10, or 10:00–11:00) |
| Date | Date picker | Defaults to today |
| Track | Toggle: Prefund / Settlement / All | Applies to every widget that supports it |
| Status | Multi-select: On Track / At Risk / Delayed / Failed / Waiting / Completed | |
| Last Updated | Read-only timestamp, top-right | Auto-refresh indicator |

Layout: single sticky header bar, full width, height ~64px, filters left-aligned, environment/last-updated right-aligned.

---

## 5. Business / Operations Dashboard — Widget-by-Widget Spec

### Segment A — Current Processing Window (top of page, full width)

**Widget A1: Current Window Summary Table**
- Type: Comparison table, 3 columns (Prefund | Settlement | Total) with header status badge
- Attributes per column: Requests/Transactions, Requested/Received $, Reserved/Settled $, Pending $, Failed $, Completed count, Failed count, Pending count
- Layout: full-width card, ~180px tall, pinned directly under global header

**Widget A2: Window Health**
- Type: Status strip, 4 pills
- Attributes: Prefund status, Settlement status, Fund Reservation status, Overall status (each a colored dot + label)
- Layout: full-width strip, ~60px tall, directly below A1

### Segment B — Prefund KPI Row

**Widget B1: Prefund KPI Cards**
- Type: Row of 8 single-value KPI cards
- Attributes: Requests, Transactions, Request $, Reserved $, Pending $, Failed $, Avg Response Time, P95 Response Time
- Layout: 8 equal-width cards in a single row (wrap to 4x2 on narrow screens), ~100px tall

**Widget B2: Prefund Additional Metrics (expandable row)**
- Type: Secondary KPI strip, collapsible
- Attributes: P99 Response Time, Validation Failures, Duplicate Files, Parsing Failures, Reservation Requests, Reservation Success Rate, Reservation Pending
- Layout: collapsible drawer under B1, full width

### Segment C — Settlement KPI Row

**Widget C1: Settlement KPI Cards**
- Type: Row of 8 single-value KPI cards
- Attributes: Transactions, Received $, Settled $, Pending $, Matched count, Unmatched count, Amount Mismatch $, Avg Processing Time
- Layout: mirrors B1, directly below Prefund segment

**Widget C2: Settlement Additional Metrics (expandable row)**
- Type: Secondary KPI strip, collapsible
- Attributes: P95/P99 Processing Time, Conversion Failures, Outbound File Generation status, Outbound Delivery status, Prefund Match %
- Layout: collapsible drawer under C1

### Segment D — Trend Graphs (2-column grid)

**Widget D1: Prefund Request/Transaction Volume by Window**
- Type: Multi-line chart
- Attributes: x = window, series = Requests, Reserved, Pending, Failed
- Layout: left column, ~320px tall

**Widget D2: Prefund $ Value by Window**
- Type: Multi-line/area chart
- Attributes: x = window, series = Requested $, Reserved $, Pending $, Failed $
- Layout: right column, ~320px tall, paired with D1

**Widget D3: Settlement Transaction Volume by Window**
- Type: Multi-line chart
- Attributes: x = window, series = Transactions Received, Matched, Unmatched, Failed
- Layout: left column, below D1

**Widget D4: Settlement $ Value by Window**
- Type: Multi-line/area chart
- Attributes: x = window, series = Received $, Settled $, Mismatch $
- Layout: right column, below D2

**Widget D5: Processing Response Time by Window**
- Type: Multi-line chart with threshold band
- Attributes: x = window, series = Prefund Avg/P95/P99, Settlement Avg/P95/P99, Reservation Avg/P95/P99, End-to-End; horizontal SLA threshold line
- Layout: left column, below D3

**Widget D6: Window SLA / Health History**
- Type: Horizontal status timeline (swimlane per track)
- Attributes: lane = Prefund/Settlement/Reservation/Overall, cell per window colored by status
- Layout: right column, below D4, height matched to D5

### Segment E — Fund Reservation & Risk (2-column grid)

**Widget E1: Fund Reservation Panel**
- Type: KPI grid (2x4)
- Attributes: Requests, Reserved, Pending, Failed, Requested $, Reserved $, Pending $, Failed $, plus sub-row Avg/P95 Response Time, Retries, Timeouts
- Layout: left column, ~220px tall

**Widget E2: Pending / Amount-at-Risk Panel**
- Type: Stacked bar or waterfall + summary total
- Attributes: Prefund Pending $, Settlement Pending $, Reservation Pending $, Failed $, Total At Risk $ (bold summary line)
- Layout: right column, matched height to E1

### Segment F — Failure Trend & Comparison (2-column grid)

**Widget F1: Failed Processing by Window**
- Type: Grouped bar chart + table toggle
- Attributes: x = window, series = Prefund Failed (count/$), Settlement Failed (count/$); filterable by failure category (File / Transaction / Reservation / Matching / Conversion / Outbound)
- Layout: left column, ~280px tall

**Widget F2: Prefund vs. Settlement Comparison Table**
- Type: Data table
- Attributes: columns = Window, Prefund Requests, Prefund $, Settlement Transactions, Settlement $
- Layout: right column, matched height to F1

### Segment G — Lifecycle Flow (full width, bottom)

**Widget G1: Prefund → Settlement Lifecycle Flow**
- Type: Sankey/funnel diagram
- Attributes: nodes = Prefund Requests ($, count) → Reservation outcome (Reserved/Pending/Failed, $ and count) → Settlement Received ($, count) → Match outcome (Matched/Unmatched, $ and count)
- Layout: full width, ~300px tall, final widget on the page

### Business Dashboard — Full Page Layout Summary

```
[ Header: Filters + Environment + Last Updated ]
[ A1 Current Window Summary (full width) ]
[ A2 Window Health (full width) ]
[ B1 Prefund KPI cards (full width) ]  [ B2 collapsible ]
[ C1 Settlement KPI cards (full width) ] [ C2 collapsible ]
[ D1 Prefund Volume Trend      | D2 Prefund $ Trend        ]
[ D3 Settlement Volume Trend   | D4 Settlement $ Trend     ]
[ D5 Response Time Trend       | D6 SLA/Health Timeline    ]
[ E1 Fund Reservation Panel    | E2 Pending/At-Risk Panel  ]
[ F1 Failure Trend             | F2 Prefund vs Settlement  ]
[ G1 Lifecycle Flow (full width) ]
```

---

## 6. Support Dashboard — Widget-by-Widget Spec

### Segment A — Support KPI Row (top, full width)

**Widget A1: Support KPI Cards**
- Type: Row of 7 single-value KPI cards, click-through enabled
- Attributes: Windows At Risk, Prefund Failures (count), Reservation Pending, Settlement Exceptions, Failed $/At Risk $, Retry Exhausted, Reconciliation Required
- Layout: full-width row, ~100px tall, each card clickable to jump to the relevant detail widget

### Segment B — Windows Requiring Attention (full width, always visible)

**Widget B1: Exception Queue Table**
- Type: Sortable/filterable data table
- Attributes: columns = Window, Type (Prefund/Settlement), Status, Transactions, $ Value, Problem, Recommended Action; row click opens drill-down drawer
- Layout: full width, ~300px tall, positioned directly under KPI row (highest priority position on page)

### Segment C — Drill-Down Drawer (triggered from B1, overlay or side panel)

**Widget C1: File Detail Panel**
- Type: Vertical step timeline
- Attributes: File ID, Type, Window, $ Value, Status; steps = Received, Validated, Parsed, Transactions Created, Reservation, Retry, Completed — each with timestamp and pass/fail icon
- Layout: drawer, ~400px wide, right-side slide-in

**Widget C2: Transaction Timeline**
- Type: Vertical event log, dual-track (Prefund stage / Settlement stage)
- Attributes: Transaction ID, Type, Amount, Window; Prefund events (Request Created, Transaction Persisted, Reservation Request Sent, MQ Accepted, Timeout, Retry #, Reservation Successful); Settlement events (Settlement Received, Prefund Matched, Amount Validated, Converted, Outbound Generated, Sent, Completed) — each with timestamp
- Layout: nested within drawer, scrollable, opened from C1 or directly from B1

### Segment D — Response Time & Errors (2-column grid)

**Widget D1: Response-Time Anomaly Table**
- Type: Data table with inline status icon and drill-down
- Attributes: columns = Window, Prefund Avg/P95, Settlement Avg/P95, Reservation P95, Status (🟢/🟡/🔴); row click drills into Processing Type → Processing Stage → Dependency → Error/Latency, surfacing the primary bottleneck stage
- Layout: left column, ~320px tall

**Widget D2: Error / Failure Analysis Table**
- Type: Data table, expandable rows
- Attributes: columns = Error Code, Count, Failed $, Component, Root Cause, Retryable (Y/N), Recovery Status; expanded row shows Root Cause detail, Impact ($, transaction count), Current Action, Next Recommended Action
- Layout: right column, matched height to D1

### Segment E — Pending Aging & Reservation (2-column grid)

**Widget E1: Pending Aging**
- Type: Bucketed bar chart + table
- Attributes: buckets = <1 min, 1–5 min, 5–10 min, 10–30 min, >30 min; each bucket shows count and $; >30 min bucket flagged red and clickable to affected windows/transactions
- Layout: left column, ~260px tall

**Widget E2: Fund Reservation Diagnostic**
- Type: KPI grid + mini trend
- Attributes: Requests, Reserved, Pending, Failed, Requested $, Reserved $, Pending $, Failed $, Avg/P95 Response Time, Retry Trend (Attempt 1/2/3/Exhausted), Timeouts
- Layout: right column, matched height to E1

### Segment F — Exceptions by Track (2-column grid)

**Widget F1: Prefund Exceptions Panel**
- Type: Table/list
- Attributes: Validation Failures, Duplicate Files, Parsing Failures, Reservation Timeouts, Reservation Retries — each with count, $, and link to affected transactions
- Layout: left column, ~220px tall

**Widget F2: Settlement Exceptions Panel**
- Type: Table/list
- Attributes: Unmatched Transactions, Amount Mismatches, Conversion Failures, Outbound Delivery Failures — each with count, $, and link to affected transactions
- Layout: right column, matched height to F1

### Support Dashboard — Full Page Layout Summary

```
[ Header: Filters + Environment + Last Updated ]
[ A1 Support KPI cards (full width) ]
[ B1 Windows Requiring Attention (full width) ]
[ D1 Response-Time Anomalies   | D2 Error/Failure Analysis ]
[ E1 Pending Aging             | E2 Fund Reservation Diagnostic ]
[ F1 Prefund Exceptions        | F2 Settlement Exceptions  ]
( C1 File Detail + C2 Transaction Timeline render as an on-demand
  drill-down drawer triggered from any row in B1, D1, D2, E1, F1, F2 )
```

---

## 7. Business vs. Support — design contract

| Dimension | Business/Operations | Support |
|---|---|---|
| Primary dimension | Processing Window | Processing Window |
| Primary question | What happened? | What is wrong? |
| Files | Metadata only | Individual file drill-down |
| Transactions | Volume + $ | Individual transaction |
| Failures | Count + failed $ | Error + root cause |
| Response time | Trend | Anomaly detection |
| Reservation | Business outcome (reserved/pending/failed $) | MQ/dependency diagnostic |
| Pending | Count + $ | Aging + root cause |
| Drill-down | Optional | Essential, always one click away |
| Recovery | Summary rollup | Actionable recovery workflow |

**Governing principle:** Business/Operations is dollar- and window-oriented; Support is exception-, latency-, and transaction-oriented. File count is de-emphasized everywhere in favor of request/transaction volume and dollar value, since production runs one file per window.

## 8. Metric Priority (for build sequencing)

Build in this order of priority:
1. Prefund Requests / Transactions, Prefund $ Value, Reserved $, Pending $, Failed $
2. Settlement Transactions, Settlement $, Failed $
3. Reservation Response Time (Avg/P95/P99) — the key real dependency latency
4. Settlement Matching (matched/unmatched/mismatch)
5. Retries/Timeouts
6. File count and infrastructure health (lowest priority, drill-down only)

## 9. Technical / Build Requirements

- **Window configuration** must be externalized (window size, window start alignment, environment) and read dynamically by all widgets — verify no widget assumes a fixed 10- or 60-minute cadence.
- Data feeds needed from the core Prefund/Settlement system of record:
  - Prefund file/transaction/request events with amounts and timestamps
  - Fund reservation request/response/retry/timeout events with amounts and timestamps
  - Settlement file/transaction events with amounts, match status, and timestamps
  - Error/exception records with error code, component, root cause, retryability, and linked transaction/window IDs
- Support drill-down navigation (Window → File → Batch → Transaction → Event → Error → Recovery) as a consistent click-through pattern across every relevant widget.
- Status thresholds (ON TRACK / AT RISK / DELAYED / FAILED) should be configurable per environment, since test and production will have different acceptable latency/volume bands.
- Both dashboards should support the same underlying data model so Support can pivot from a Business-dashboard anomaly straight into its own drill-down without re-querying.

## 10. Illustrative Sample Data (for prototyping only)

Use these sample series to prototype trend widgets before wiring real data feeds:

**Prefund request volume by window** — columns: window, requests, reserved, pending, failed.
**Prefund $ value by window** — columns: window, requested $, reserved $, pending $.
**Settlement volume/value by window** — columns: window, transactions, received $, settled $.
**Response time by window** — columns: window, Prefund avg/P95, Settlement avg/P95, Reservation avg/P95.

(Sample rows can be generated at 10-minute test-window cadence, e.g. 08:00, 08:10, 08:20 … through 09:00, with realistic increasing volume/$ trends and occasional latency spikes to exercise the AT RISK/FAILED status logic.)
