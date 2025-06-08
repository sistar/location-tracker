import json

# This is a mock handler for testing purposes
# It returns sample driver logs with timestamps in epoch format (seconds since Unix epoch)
# as per the updated DynamoDB schema


def handler(event, context):
    # Print debug info
    print("Event received:", json.dumps(event))

    # Always return a success response with sample data
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,GET",
        },
        "body": json.dumps(
            {
                "logs": [
                    {
                        "id": "sample_session_1",
                        "timestamp": 1743998400,  # 2025-04-08T18:30:00 in epoch
                        "timestamp_str": "2025-04-08T18:30:00",  # Human-readable version
                        "startTime": 1743996600,  # 2025-04-08T18:00:00 in epoch
                        "endTime": 1743998400,  # 2025-04-08T18:30:00 in epoch
                        "distance": 5000,
                        "duration": 30,
                        "purpose": "business",
                        "notes": "Sample trip 1",
                        "startAddress": "123 Main St",
                        "endAddress": "456 Park Ave",
                    },
                    {
                        "id": "sample_session_2",
                        "timestamp": 1743995400,  # 2025-04-08T17:30:00 in epoch
                        "timestamp_str": "2025-04-08T17:30:00",  # Human-readable version
                        "startTime": 1743993600,  # 2025-04-08T17:00:00 in epoch
                        "endTime": 1743995400,  # 2025-04-08T17:30:00 in epoch
                        "distance": 3000,
                        "duration": 30,
                        "purpose": "personal",
                        "notes": "Sample trip 2",
                        "startAddress": "456 Park Ave",
                        "endAddress": "789 Oak Rd",
                    },
                ]
            }
        ),
    }
