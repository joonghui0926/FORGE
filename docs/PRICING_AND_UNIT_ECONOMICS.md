# FORGE pricing and unit economics

As of 2026-08-15. Currency is USD. Public competitor prices were not found; they route
physical-AI buyers to sales or demo calls. Do not manufacture a per-hour competitor price.

## Decision

Sell a **validated capability package**, not raw video and not a count of synthetic rows.
The billable unit is an accepted source demonstration plus embodiment-specific episodes
that passed an independent physics replay and include rights, lineage, checksums, and the
customer's requested export.

Recommended launch prices:

| Offer | Price | Included |
| --- | ---: | --- |
| Paid feasibility | $2,500-$5,000 | task/robot contract, capture plan, 3-5 source trials, reconstruction and replay risk report; credit toward a pilot |
| Single-skill pilot | **$15,000-$25,000** | one skill, one target embodiment, 20-50 accepted sources, 250-1,000 replay-validated episodes, lineage and one export |
| Production capability | $35,000-$75,000 | one skill/embodiment, 2,000-10,000 validated episodes, larger coverage matrix, failure/recovery set and acceptance report |
| Enterprise program | from $150,000/year | multiple skills/embodiments, reserved throughput, private deployment and negotiated SLA |

The minimum quote is `max($15,000, fully_loaded_COGS / (1 - target_margin))`. Use a 67%
target gross margin until real Terac, expert, rejection, GPU and customer-support data exist.
A pilot with $5,000 fully loaded COGS therefore needs at least $15,151.52, rounded upward
in a proposal. Card processing, taxes and sales commission sit inside fully loaded COGS.

## Ten-user infrastructure budget

This is a planning budget, not an invoice. It excludes Terac worker payments, expert
premiums, paid model APIs, sales tax, card processing and support labor.

| Component | Recommended assumption | Monthly |
| --- | --- | ---: |
| Render | Pro workspace $25 + $100 service/DB budget + 20 standard Workflow hours at $0.20/hour | $129.00 |
| Pioneer | two Pro seats at $20/seat; each includes $40/seat in platform credits | $40.00 |
| Cloudflare R2 | 200 GB-month Standard, first 10 GB free; operations remain below free tier | $2.85 |
| RunPod | one A40 Pod for 8 hours/day, 22 days, at $0.44/hour | $77.44 |
| **Total control-plane + planned GPU** | | **$249.29/month** |

Keep the A40 stopped when no compiler job is running. A continuously running A40 is
$321.20 for a 730-hour month before storage. An A100 PCIe 80 GB at $1.39/hour is $11.12
for one eight-hour benchmark or $244.64 for the same 176-hour monthly schedule. Buy A100
time only when profiling proves a memory or throughput bottleneck; ten web users do not
justify ten GPUs because GPU compilation is an asynchronous queue.

The $100 Render compute/DB line is an internal budget envelope because Render's exact
service and flexible Postgres configuration has not been selected. Replace it with the
actual invoice after deployment. R2 Class A/B requests are assumed below the published
monthly free tiers. Domain registration is also excluded until a domain is selected.

Official price evidence:

- [RunPod GPU pricing](https://www.runpod.io/pricing): A40 Pod $0.44/hour; A100 PCIe
  80 GB $1.39/hour; Serverless A40/A6000 $1.22/hour.
- [Cloudflare R2 pricing](https://developers.cloudflare.com/r2/pricing/): Standard
  $0.015/GB-month, 10 GB-month free, 1M Class A and 10M Class B operations free, egress free.
- [Render workspace plans](https://render.com/docs/new-workspace-plans): Pro is $25/month
  flat with unlimited members; [Workflow pricing](https://render.com/docs/workflows-limits)
  lists Standard tasks at $0.20/hour.
- [Pioneer pricing](https://docs.pioneer.ai/pricing): Pro is $20/seat/month and includes
  $40/seat/month in platform credits; additional usage uses purchased credits.

## Competitive position

| Company | Public output/approach | FORGE wedge | Public price |
| --- | --- | --- | --- |
| Scale Physical AI | global collection, robotless egocentric and robot data, annotations, model-performance validation; 1,000+ hours/day | smaller customer-owned, embodiment-specific delivery with source-to-episode proof and explicit replay gates | not published; book a demo |
| Config Loop | collect, curate, convert, train, deploy and evaluate; human-to-robot conversion and teleop; strongest public focus is bimanual manipulation | support human, robot-state, teleop, simulation, locomotion, aerial, mobile and multi-robot sources through one IR | not published; contact team |
| Cortex | egocentric pose/depth/subtasks, workplace robot trajectories and HITL rollout/eval | deterministic physics evidence and delivery contract rather than an annotation-only package | not published; get in touch |

Sources: [Scale Physical AI](https://scale.com/physical-ai),
[Config Loop](https://config.inc/products/loop), and [Cortex](https://cortexrobot.ai/).

FORGE cannot win on collection volume at launch. It should win on a narrow guarantee:
**every delivered episode is traceable to a licensed source, target embodiment and exact
compiler/model versions, and has passed a motion-specific replay profile**. Quality failures
remain in the rejection report instead of being silently removed. Generated variants never
inherit source acceptance; each is replayed again.

## Quote inputs still required

Before sending a fixed customer quote, obtain: Terac assignment and expert rates, expected
source rejection rate, average minutes of source video, RunPod stage timings by GPU,
third-party API spend, target episode count, target robot/simulator integration work,
delivery bandwidth, support hours, payment method and rights/insurance requirements.

Confidence: **share with caveats**. Infrastructure prices are official and current; service
compute, labor, throughput and competitor deal sizes need actual quotes and benchmark data.
