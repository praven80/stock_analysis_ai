# Stock Analysis Agent

A sophisticated stock analysis platform powered by AWS Bedrock Agents, providing real-time market insights and analysis through a user-friendly Streamlit interface.

You can view a short demo video in the "Demo" folder.

## Features

- Real-time stock data analysis
- News aggregation and analysis
- Multi-agent architecture
- Interactive web interface
- Automated insights generation
- Step-by-step analysis tracking

## Architecture

### Agents
1. News Agent
   - Fetches latest relevant news for stocks
   - Web search capabilities
   - Historical news retrieval

2. Stock Data Agent
   - Real-time stock data retrieval
   - Price trend analysis
   - Technical indicators

3. Analyst Agent
   - Data interpretation
   - Market analysis
   - Strategic recommendations

4. Portfolio Assistant
   - Orchestrates other agents
   - Generates comprehensive reports
   - Investment considerations

## Prerequisites

- AWS Account with access to:
  - AWS Bedrock
  - Amazon ECS
  - AWS IAM
  - AWS Lambda
- Python 3.9+
- Docker
- AWS CDK

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd stock-analysis-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install AWS CDK (if not already installed):
```bash
npm install -g aws-cdk
```

4. Bootstrap CDK (first time only):
```bash
cdk bootstrap
```

## Deployment

1. Configure AWS credentials:
```bash
aws configure
```

2. Deploy the stack:
```bash
cdk deploy
```

## Environment Variables

Required environment variables:
```
AGENT_ID=<bedrock-agent-id>
AGENT_ALIAS_ID=<bedrock-agent-alias-id>
```

## Usage

1. Access the application through the provided ALB DNS
2. Enter a stock ticker symbol
3. View real-time analysis and insights

## Infrastructure

The application is deployed using:
- Amazon ECS (Fargate)
- Application Load Balancer
- VPC with public/private subnets
- CloudWatch Logs
- IAM roles and policies

## Docker Support

Build the container:
```bash
docker build -t stock-analysis-agent .
```

Run locally:
```bash
docker run -p 8501:8501 stock-analysis-agent
```

## Development

### Local Development
```bash
streamlit run app.py
```

### Adding New Features
1. Modify the agent configurations in `create_bedrock_agents.py`
2. Update the Streamlit interface in `app.py`
3. Deploy changes using CDK

## Security

- Private subnets for container deployment
- Security groups for network access control
- VPC isolation