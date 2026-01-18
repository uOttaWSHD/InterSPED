#!/bin/bash

# Interactive Interview Chat with DeliveryAgent
# Maintains conversation context for a continuous interview session

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"
AGENT_NAME="${AGENT_NAME:-DeliveryAgent}"
REQUEST_ID=1
CONTEXT_ID=""

# Interview context JSON
INTERVIEW_CONTEXT='{
  "company": "RBC",
  "opening": "Hello, my name is John and I am a software engineer at RBC. Can you start by telling me a little bit about your background and experience?",
  "questions": [
    "Tell me about a time when you had to debug a complex issue in a large-scale system. How did you approach it and what was the outcome?",
    "Design a system to handle high-volume transactions in a banking environment. How would you ensure scalability, security, and reliability?"
  ],
  "coding": {
    "title": "Transaction Processing",
    "desc": "Write a program to process a list of transactions and calculate the total balance",
    "example": "[{id: 1, amount: 100}, {id: 2, amount: -50}] => 50"
  },
  "tech_stack": ["Java", "Python", "C++", "Spring"],
  "domain": "finance, banking",
  "focus": ["technical skills", "problem-solving", "system design"]
}'

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}     RBC Mock Interview - Interactive Chat${NC}"
echo -e "${YELLOW}================================================${NC}"
echo ""
echo -e "Company: ${GREEN}RBC${NC}"
echo -e "Type your responses and press Enter."
echo -e "Type ${GREEN}'quit'${NC} or ${GREEN}'exit'${NC} to end the session."
echo ""
echo -e "${YELLOW}Starting interview...${NC}"
echo ""

# Function to send message and get response
send_message() {
    local message="$1"
    local response=""
    
    # Build the request - include contextId if we have one for conversation continuity
    local context_field=""
    if [ -n "$CONTEXT_ID" ]; then
        context_field="\"contextId\": \"$CONTEXT_ID\","
    fi
    
    # Send request and capture response
    response=$(curl -s -X POST "$GATEWAY_URL/api/v1/message:stream" \
      -H "Content-Type: application/json" \
      -H "Accept: application/json" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"id\": $REQUEST_ID,
        \"method\": \"message/stream\",
        \"params\": {
          $context_field
          \"message\": {
            \"messageId\": \"msg_${REQUEST_ID}_$(date +%s)\",
            \"kind\": \"message\",
            \"role\": \"user\",
            \"metadata\": {
              \"agent_name\": \"$AGENT_NAME\",
              \"context\": $INTERVIEW_CONTEXT
            },
            \"parts\": [
              {
                \"kind\": \"text\",
                \"text\": \"$message\"
              }
            ]
          }
        }
      }")
    
    # Extract contextId for future messages
    local new_context=$(echo "$response" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data.get('result',{}).get('contextId',''))" 2>/dev/null)
    if [ -n "$new_context" ]; then
        CONTEXT_ID="$new_context"
    fi
    
    # Extract task ID to poll for results
    local task_id=$(echo "$response" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data.get('result',{}).get('id',''))" 2>/dev/null)
    
    if [ -z "$task_id" ]; then
        echo -e "${YELLOW}Error: Could not get task ID${NC}"
        echo "$response"
        return
    fi
    
    # Poll for the task result using SSE endpoint
    echo -ne "${BLUE}Interviewer: ${NC}"
    
    # Use the events endpoint to get streaming response
    curl -s -N "$GATEWAY_URL/api/v1/tasks/$task_id/events" \
      -H "Accept: text/event-stream" 2>/dev/null | while IFS= read -r line; do
        # Parse SSE data lines
        if [[ "$line" == data:* ]]; then
            data="${line#data:}"
            # Extract text content from the response
            text=$(echo "$data" | python3 -c "
import sys,json
try:
    data = json.load(sys.stdin)
    # Check for text in artifact or message parts
    if 'artifact' in data:
        parts = data.get('artifact',{}).get('parts',[])
        for p in parts:
            if p.get('kind') == 'text':
                print(p.get('text',''), end='')
    elif 'status' in data:
        msg = data.get('status',{}).get('message',{})
        if msg:
            parts = msg.get('parts',[])
            for p in parts:
                if p.get('kind') == 'text':
                    print(p.get('text',''), end='')
    elif 'result' in data:
        parts = data.get('result',{}).get('status',{}).get('message',{}).get('parts',[])
        for p in parts:
            if p.get('kind') == 'text':
                print(p.get('text',''), end='')
except:
    pass
" 2>/dev/null)
            if [ -n "$text" ]; then
                echo -n "$text"
            fi
        fi
        
        # Check if task is complete
        if [[ "$line" == *'"state":"completed"'* ]] || [[ "$line" == *'"state":"failed"'* ]]; then
            break
        fi
    done
    
    echo ""
    echo ""
    
    ((REQUEST_ID++))
}

# Start the interview with initial greeting
send_message "Hi, I am ready for the interview."

# Main chat loop
while true; do
    echo -ne "${GREEN}You: ${NC}"
    read -r user_input
    
    # Check for exit commands
    if [[ "$user_input" == "quit" ]] || [[ "$user_input" == "exit" ]] || [[ "$user_input" == "q" ]]; then
        echo ""
        echo -e "${YELLOW}Interview session ended. Good luck!${NC}"
        break
    fi
    
    # Skip empty input
    if [ -z "$user_input" ]; then
        continue
    fi
    
    # Send message and display response
    send_message "$user_input"
done
