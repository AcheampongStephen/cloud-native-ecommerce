# Pending checkout recovery

1. Identify the order through the authenticated order list. Record its ID/status,
   original request and retry key privately.
2. Check Order, Inventory and Payment readiness/logs. A timeout may follow a
   successful remote commit; do not assume no payment/reservation exists.
3. Restore unavailable dependencies.
4. Sign in as the owner and select Resume checkout under My orders. This sends
   the original request/key and reuses existing reservation/payment outcomes.
5. Confirm final order state, available stock and exactly one payment record.
6. For confirmed orders, verify the notification arrives. Escalate unresolved
   conflicting states; do not manually release stock after an approved payment
   without reconciling the entire workflow.

There is no automatic reconciler or reservation timeout. Use this procedure for
abandoned pending orders; build an audited reconciler before production use.
