#!/bin/bash

# Simple curl example to send a request to the Delivery Agent
# This is a minimal version without all the formatting

# Variables
GATEWAY_URL="http://localhost:8000"
AGENT_NAME="DeliveryAgent"
MESSAGE="I was asked about a challenge I faced. I overcame a performance issue by profiling the code and optimizing the bottleneck."

# Simple curl command to stream agent response
curl -N -X POST "$GATEWAY_URL/api/v1/message:stream" \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": 1,
    \"method\": \"message/stream\",
    \"params\": {
      \"message\": {
        \"messageId\": \"msg_\$(date +%s)\",
        \"kind\": \"message\",
        \"role\": \"user\",
        \"metadata\": {
          \"agent_name\": \"$AGENT_NAME\"
        },
        \"parts\": [
          {
            \"kind\": \"text\",
            \"text\": \"$MESSAGE\"
          }
        ]
      }
    }
  }"
