# Billing Agent Spec
- **Route**: Should route to billing sub-agent.
- **Verification**: Must verify user details before granting refund.
- **Handoff**: Set parameter `callType` to "billing_dispute" and transfer if customer rejects alternatives.
