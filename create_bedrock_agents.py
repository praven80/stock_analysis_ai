import boto3
import time
import uuid
from datetime import datetime
import sys
import json

# Check if enough arguments are provided
if len(sys.argv) < 2:
    print("Usage: python script.py <iam_role_arn>")
    sys.exit(1)

# Extract the IAM Role ARN from the command-line arguments
iam_role_arn = sys.argv[1]

# Custom JSON serializer for datetime objects
def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()  # Convert datetime to ISO format string
    raise TypeError("Type not serializable")

# Initialize the Bedrock Agent client
def initialize_bedrock_agent_client():
    return boto3.client(
        'bedrock-agent'
    )

# Create an agent
def create_agent(bedrock_agent_client, agent_name, foundation_model, description, agent_resource_role_arn, instruction, tags, agent_collaboration='DISABLED'):
    agent_response = bedrock_agent_client.create_agent(
        agentCollaboration=agent_collaboration,
        agentName=agent_name,
        agentResourceRoleArn=agent_resource_role_arn,
        description=description,
        foundationModel=foundation_model,
        instruction=instruction,
        tags=tags
    )
    return agent_response['agent']['agentId']

# Create an action group for an agent
def create_agent_action_group(bedrock_agent_client, agent_id, action_group_name, action_group_executor, action_group_state, description, function_schema):
    client_token = str(uuid.uuid4())  # Generate a unique token
    action_group_response = bedrock_agent_client.create_agent_action_group(
        actionGroupExecutor=action_group_executor,
        actionGroupName=action_group_name,
        actionGroupState=action_group_state,
        agentId=agent_id,
        agentVersion='DRAFT',
        clientToken=client_token,
        description=description,
        functionSchema=function_schema
    )
    return action_group_response

# Prepare an agent
def prepare_agent(bedrock_agent_client, agent_id):
    prepare_response = bedrock_agent_client.prepare_agent(
        agentId=agent_id
    )
    return prepare_response['agentStatus']

# Create an agent alias for the prepared agent
def create_agent_alias(bedrock_agent_client, agent_id, agent_alias_name):
    client_token = str(uuid.uuid4())  # Unique client token for alias creation
    agent_alias_response = bedrock_agent_client.create_agent_alias(
        agentAliasName=agent_alias_name,
        agentId=agent_id,
        description='Alias for the agent',
        tags={
            'Environment': 'Production',
            'Project': 'AgentProject'
        }
    )
    return agent_alias_response

# Associate a collaborator with an agent
def associate_agent_collaborator(bedrock_agent_client, agent_id, collaborator_name, agent_descriptor):
    associate_response = bedrock_agent_client.associate_agent_collaborator(
        agentDescriptor=agent_descriptor,
        agentId=agent_id,
        agentVersion='DRAFT',
        collaborationInstruction="Collaborator will help with agent training",
        collaboratorName=collaborator_name
    )
    return associate_response

def create_agent_alias_descriptor(bedrock_agent_client, agent_name):
    print("Inside Alias")
    print(f"Agent name: {agent_name}")

    # List agents to find the agentId for the given agent name
    list_agents_response = bedrock_agent_client.list_agents(maxResults=123)
    agent_id = None
    for existing_agent in list_agents_response['agentSummaries']:
        if existing_agent['agentName'] == agent_name:
            agent_id = existing_agent['agentId']
            break

    print(f"Agent ID: {agent_id}")

    # List agent aliases for the given agentId
    alias_name = f"{agent_name}Alias"
    list_aliases_response = bedrock_agent_client.list_agent_aliases(agentId=agent_id)
    print(f"List aliases response: {list_aliases_response}")
    agent_alias_summaries = list_aliases_response.get('agentAliasSummaries', [])

    # Return the alias ARN if found
    for alias in agent_alias_summaries:
        if alias['agentAliasName'] == alias_name:
            get_agent_alias_response = bedrock_agent_client.get_agent_alias(agentAliasId=alias['agentAliasId'], agentId=agent_id)
            return {'aliasArn': get_agent_alias_response['agentAlias']['agentAliasArn']}

    # If not found, create a new agent alias and return its ARN
    create_agent_alias_response = bedrock_agent_client.create_agent_alias(
        agentAliasName=alias_name,
        agentId=agent_id,
        description=f"Alias for the {agent_name} agent",
        tags={
            'Environment': 'Production',
            'Project': 'AgentProject'
        }
    )
    return {'aliasArn': create_agent_alias_response['aliasArn']}

def main():
    
    # Get AWS account and region details
    session = boto3.session.Session()
    region = session.region_name

    sts_client = boto3.client("sts")
    account_id = sts_client.get_caller_identity()["Account"]

    bedrock_agent_client = initialize_bedrock_agent_client()

    agents = [
        {
            'agent_name': 'news_agent',
            # 'foundation_model': "anthropic.claude-3-5-haiku-20241022-v1:0",
            'foundation_model': "anthropic.claude-3-haiku-20240307-v1:0",
            'description': 'News agent',
            'instruction': "Role: Market News Researcher, Goal: Fetch latest relevant news for a given stock based on a ticker., Instructions: Top researcher in financial markets and company announcements.",
            'action_group_name': 'actions_news_agent',
            'action_group_executor': {'lambda': f'arn:aws:lambda:{region}:{account_id}:function:web_search'},
            
            'action_group_function_name': 'web_search',
            'parameters': [
                {
                    'name': 'days',
                    'description': "The number of days of history to search. Helps when looking for recent events or news."
                },
                {
                    'name': 'search_query',
                    'description': "The query to search the web with"
                },
                {
                    'name': 'target_website',
                    'description': "The specific website to search including its domain name. If not provided, the most relevant website will be used"
                },
                {
                    'name': 'topic',
                    'description': "The topic being searched. 'news' or 'general'. Helps narrow the search when news is the focus."
                }
            ]
        },
        {
            'agent_name': 'stock_data_agent',
            # 'foundation_model': "anthropic.claude-3-5-haiku-20241022-v1:0",
            'foundation_model': "anthropic.claude-3-haiku-20240307-v1:0",
            'description': 'Stock data agent',
            'instruction': "Role: Financial Data Collector, Goal: Retrieve accurate stock trends for a given ticker., Instructions: Specialist in real-time financial data extraction.",
            'action_group_name': 'actions_stock_data_agent',
            'action_group_executor': {'lambda': f'arn:aws:lambda:{region}:{account_id}:function:stock_data_lookup'},
            'action_group_function_name': 'stock_data_lookup',
            'parameters': [
                {
                    'name': 'ticker',
                    'description': "The ticker to retrieve price history for"
                }
            ]
        },
        {
            'agent_name': 'analyst_agent',
            # 'foundation_model': "anthropic.claude-3-5-haiku-20241022-v1:0",
            'foundation_model': "anthropic.claude-3-haiku-20240307-v1:0",
            'description': 'Analyst agent',
            'instruction': "Role: Financial Analyst, Goal: Analyze stock trends and market news to generate insights., Instructions: Experienced analyst providing strategic recommendations. You take as input the news summary and stock price summary. You have no available tools. Rely only on your own knowledge.",
            'action_group_name': None,
            'action_group_executor': None,
            'action_group_function_name': None,
            'parameters': None
        },
        {
            'agent_name': 'portfolio_assistant',
            # 'foundation_model': "anthropic.claude-3-5-haiku-20241022-v1:0",
            'foundation_model': "anthropic.claude-3-haiku-20240307-v1:0",
            'description': 'Portfolio assistant',
            'instruction': "Act as a seasoned expert at analyzing a potential stock investment for a given stock ticker. Do your research to understand how the stock price has been moving lately, as well as recent news on the stock. Give back a well written and carefully considered report with considerations for a potential investor. You use your analyst collaborator to perform the final analysis, and you give the news and stock data to the analyst as input. Use your collaborators in sequence, not in parallel.",
            'action_group_name': None,
            'action_group_executor': None,
            'action_group_function_name': None,
            'parameters': None
        }
    ]

    for agent in agents:
        try:
            # List all agents to find the agentId for the given agent name
            print(f"Listing agents to find the agent ID for '{agent['agent_name']}'...")
            list_agents_response = bedrock_agent_client.list_agents(maxResults=123)

            # Find the agentId for the given agent name
            agent_id = None
            for existing_agent in list_agents_response['agentSummaries']:
                if existing_agent['agentName'] == agent['agent_name']:
                    agent_id = existing_agent['agentId']
                    print(f"Found agent '{agent['agent_name']}' with agentId '{agent_id}'")
                    break

            # If the agent exists, delete it
            if agent_id:
                print(f"Deleting existing agent '{agent['agent_name']}' with agentId '{agent_id}'...")
                delete_response = bedrock_agent_client.delete_agent(
                    agentId=agent_id,
                    skipResourceInUseCheck=True  # Skipping resource check to force delete
                )

                # Wait for the agent to be fully deleted
                print("Waiting for agent deletion to complete...")
                while True:
                    time.sleep(5)  # Poll every 5 seconds to check for deletion
                    try:
                        get_agent_response = bedrock_agent_client.get_agent(agentId=agent_id)
                    except bedrock_agent_client.exceptions.ResourceNotFoundException:
                        print(f"Agent '{agent['agent_name']}' successfully deleted.")
                        break

            # Create the agent after deletion or if it did not exist
            print(f"Creating agent '{agent['agent_name']}'...")
            if agent['agent_name'] == 'portfolio_assistant':
                agent_id = create_agent(bedrock_agent_client, agent['agent_name'], agent['foundation_model'], agent['description'], iam_role_arn, agent['instruction'], {
                    'Environment': 'Production',
                    'Project': 'AgentProject'}, 'SUPERVISOR')
            else:
                agent_id = create_agent(bedrock_agent_client, agent['agent_name'], agent['foundation_model'], agent['description'], iam_role_arn, agent['instruction'], {
                    'Environment': 'Production',
                    'Project': 'AgentProject'})

            # Wait until the agent is in a valid state before preparing it
            print(f"Waiting for agent '{agent['agent_name']}' to be in a valid state...")
            while True:
                time.sleep(5)  # Poll every 5 seconds to check the agent's status
                get_agent_response = bedrock_agent_client.get_agent(agentId=agent_id)
                agent_status = get_agent_response['agent']['agentStatus']

                if agent_status in ['PREPARED', 'NOT_PREPARED']:
                    if agent['agent_name'] == 'portfolio_assistant':
                        print(f"Agent '{agent['agent_name']}' is in a valid state: {agent_status}. Proceeding to add collaborators.")
                        break
                    else:
                        print(f"Agent '{agent['agent_name']}' is in a valid state: {agent_status}. Proceeding to prepare.")
                        break
                elif agent_status == 'FAILED':
                    print(f"Agent '{agent['agent_name']}' creation failed.")
                    break
                else:
                    print(f"Agent '{agent['agent_name']}' is still in '{agent_status}' state. Retrying...")

            if agent['agent_name'] == 'portfolio_assistant':
                print("Adding Collabs")
                # Add collaborators
                collaborator_agents = [
                    {
                        'collaborator_name': 'news_agent',
                        'agent_descriptor': create_agent_alias_descriptor(bedrock_agent_client, 'news_agent')
                    },
                    {
                        'collaborator_name': 'stock_data_agent',
                        'agent_descriptor': create_agent_alias_descriptor(bedrock_agent_client, 'stock_data_agent')
                    },
                    {
                        'collaborator_name': 'analyst_agent',
                        'agent_descriptor': create_agent_alias_descriptor(bedrock_agent_client, 'analyst_agent')
                    }
                ]
                for collaborator in collaborator_agents:
                    try:
                        print(f"Adding collaborator '{collaborator['collaborator_name']}' to agent '{agent['agent_name']}'...")
                        print(f"Agent ID: {agent_id}")
                        print(f"Collaborator Descriptor: {collaborator['agent_descriptor']}")
                        print(f"Collaborator Name: {collaborator['collaborator_name']}")
                        
                        # Associate the collaborator
                        bedrock_agent_client.associate_agent_collaborator(
                            agentDescriptor=collaborator['agent_descriptor'],
                            agentId=agent_id,
                            agentVersion='DRAFT',
                            collaborationInstruction="Collaborator will help with agent training",
                            collaboratorName=collaborator['collaborator_name']
                        )
                        print(f"Collaborator '{collaborator['collaborator_name']}' added successfully.")
                    except Exception as e:
                        print(f"Error adding collaborator '{collaborator['collaborator_name']}': {e}")

                # Prepare the agent after collaborators are added
                print(f"Preparing agent '{agent['agent_name']}'...")
                prepare_agent(bedrock_agent_client, agent_id)

                # Wait until the agent is fully prepared
                print(f"Waiting for agent '{agent['agent_name']}' to be fully prepared...")
                while True:
                    time.sleep(5)  # Poll every 5 seconds to check the agent's status
                    get_agent_response = bedrock_agent_client.get_agent(agentId=agent_id)
                    print(f"Agent Response: {get_agent_response}")
                    agent_status = get_agent_response['agent']['agentStatus']
                    print(f"Agent Status: {agent_status}")

                    if agent_status == 'PREPARED':
                        print(f"Agent '{agent['agent_name']}' is fully prepared.")
                        break
                    else:
                        print(f"Agent '{agent['agent_name']}' is still in '{agent_status}' state. Retrying...")
            else:
                # Prepare the agent after it is in a valid state
                print(f"Preparing agent '{agent['agent_name']}'...")
                prepare_agent(bedrock_agent_client, agent_id)

                # Wait until the agent is fully prepared
                print(f"Waiting for agent '{agent['agent_name']}' to be fully prepared...")
                while True:
                    time.sleep(5)  # Poll every 5 seconds to check the agent's status
                    get_agent_response = bedrock_agent_client.get_agent(agentId=agent_id)
                    agent_status = get_agent_response['agent']['agentStatus']

                    if agent_status == 'PREPARED':
                        print(f"Agent '{agent['agent_name']}' is fully prepared.")
                        break
                    else:
                        print(f"Agent '{agent['agent_name']}' is still in '{agent_status}' state. Retrying...")

            # Create an action group for the agent if required
            if agent['action_group_name']:
                function_schema = {
                    'functions': [
                        {
                            'description': f"Function to {agent['action_group_function_name']}.",
                            'name': agent['action_group_function_name'],
                            'parameters': {},
                            'requireConfirmation': 'DISABLED'
                        }
                    ]
                }
                for param in agent['parameters']:
                    function_schema['functions'][0]['parameters'][param['name']] = {
                        'description': param['description'],
                        'required': True,
                        'type': 'string'
                    }
                create_agent_action_group(bedrock_agent_client, agent_id, agent['action_group_name'], agent['action_group_executor'], 'ENABLED', f"Action group to {agent['action_group_function_name']} with parameters", function_schema)

            # Create an agent alias for the prepared agent
            agent_alias_response = create_agent_alias(bedrock_agent_client, agent_id, f'{agent["agent_name"]}Alias')
            agent_alias_id = agent_alias_response['agentAlias']['agentAliasId']

        except Exception as e:
            print(f"Error: {e}")

    return agent_id, agent_alias_id

if __name__ == "__main__":
    agent_id, agent_alias_id = main()
    
    # Print output as JSON
    output = {
        "final_supervisor_agent_id": agent_id,
        "final_supervisor_agent_alias": agent_alias_id,
    }
    print(json.dumps(output))