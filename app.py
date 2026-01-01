import boto3
import uuid
import time
import streamlit as st
import os

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="Stock Analysis Agent",
    page_icon="📈",
    layout="wide"
)

# Custom CSS for consistent height and better formatting
st.markdown("""
    <style>
    .fixed-height {
        height: 400px;
        overflow-y: auto;
        border: 1px solid #ccc;
        padding: 20px;
        border-radius: 5px;
        background-color: #f8f9fa;
    }
    .step-text {
        margin-bottom: 15px;
        padding: 10px;
        background-color: white;
        border-radius: 5px;
        border: 1px solid #eee;
    }
    </style>
""", unsafe_allow_html=True)

class BedrockAgentHandler:
    def __init__(self):
        # Get AWS account and region details
        session = boto3.session.Session()
        region = session.region_name
        
        self.client = boto3.client('bedrock-agent-runtime', region_name=region)
        
        self.agent_id = os.environ.get('AGENT_ID')
        self.agent_alias_id = os.environ.get('AGENT_ALIAS_ID')
        
        self.session_id = str(uuid.uuid1())
        self.start_time = None

    def invoke_agent(self, input_text, output_placeholder, steps_container, timer_placeholder):
        try:
            step_number = 1
            current_steps = []
            
            # Initialize empty boxes with placeholders
            steps_container.markdown("""
            <div class="fixed-height">
                <div class="step-text">
                    Activating the analysis framework...
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            output_placeholder.markdown("""
            <div class="fixed-height">
                <div class="step-text">
                    Gathering the insights...
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Make API call
            response = self.client.invoke_agent(
                inputText=input_text,
                agentId=self.agent_id,
                agentAliasId=self.agent_alias_id,
                sessionId=self.session_id,
                enableTrace=True
            )

            # Process response stream
            for event in response['completion']:
                # Update timer
                elapsed = time.time() - self.start_time
                timer_placeholder.markdown(f"⏱️ Processing Time: {elapsed:.1f} seconds")
                
                # Handle output chunks
                if 'chunk' in event:
                    data = event['chunk']['bytes'].decode('utf8')
                    formatted_result = f"""
                    <div class="fixed-height">
                        <div class="step-text">
                            {data}
                        </div>
                    </div>
                    """
                    output_placeholder.markdown(formatted_result, unsafe_allow_html=True)

                # Handle trace events (steps)
                if 'trace' in event:
                    if 'trace' in event['trace']:
                        if 'orchestrationTrace' in event['trace']['trace']:
                            orch = event['trace']['trace']['orchestrationTrace']
                            
                            if 'rationale' in orch:
                                rationale_text = orch['rationale']['text']
                                
                                # Only add new steps (avoid duplicates)
                                if rationale_text not in current_steps:
                                    current_steps.append(rationale_text)
                                    st.session_state.analysis_steps.append(
                                        f'<div class="step-text">'
                                        f'<strong>Step {step_number}:</strong><br>{rationale_text}'
                                        f'</div>'
                                    )
                                    steps_html = f"""
                                    <div class="fixed-height">
                                        {''.join(st.session_state.analysis_steps)}
                                    </div>
                                    """
                                    steps_container.markdown(steps_html, unsafe_allow_html=True)
                                    step_number += 1

            return True

        except Exception as e:
            st.error(f"Error: {str(e)}")
            return False

st.title("📈 Stock Analysis Agent")
# st.markdown("Enter your ticker symbol and press Enter to begin analysis.")
st.markdown("""
    This application delivers detailed stock analysis powered by Amazon Bedrock Multi-Agents.
    Enter your ticker symbol and press Enter to begin analysis.
""")

def is_valid_ticker(ticker):
    return ticker and len(ticker) <= 5 and ticker.isalpha()

# Initialize session state for analysis steps
if 'analysis_steps' not in st.session_state:
    st.session_state.analysis_steps = []

ticker = st.text_input("Stock Ticker", key="ticker_input")

# Create a container for the success message
success_container = st.empty()

if ticker and ticker != st.session_state.get('last_analyzed_ticker', ''):
    # Clear success message from previous analysis
    success_container.empty()
    
    if not is_valid_ticker(ticker):
        st.error("Invalid ticker symbol. Please enter 1-5 letters only.")
    else:
        # Clear previous analysis steps
        st.session_state.analysis_steps = []
        st.session_state['last_analyzed_ticker'] = ticker
        
        # Create containers for spinner and timer
        spinner_row = st.empty()
        timer_placeholder = st.empty()
        
        # Create columns for headers and content
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### Analysis Steps")
            steps_container = st.empty()
            # Initialize empty box
            steps_container.markdown("""
            <div class="fixed-height">
                <div class="step-text">
                    Waiting for analysis to begin...
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("### Results")
            output_placeholder = st.empty()
            # Initialize empty box
            output_placeholder.markdown("""
            <div class="fixed-height">
                <div class="step-text">
                    Waiting for results...
                </div>
            </div>
            """, unsafe_allow_html=True)

        handler = BedrockAgentHandler()
        handler.start_time = time.time()  # Set start time
        
        # Use the spinner container above both columns
        with spinner_row:
            with st.spinner('Decoding the market pulse...'):
                success = handler.invoke_agent(
                    f"ticker {ticker}",
                    output_placeholder,
                    steps_container,
                    timer_placeholder
                )
                
                if success:
                    final_time = time.time() - handler.start_time
                    timer_placeholder.markdown(f"⏱️ Total Processing Time: {final_time:.1f} seconds")
                    success_container.success("✅ Stock Insights ready!")