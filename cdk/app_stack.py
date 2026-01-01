from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_logs as logs,
    aws_ecr_assets as ecr_assets,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
    RemovalPolicy
)
from constructs import Construct
import subprocess
import os
import json

class AppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Path to the Python script
        python_file_path = os.path.join(os.path.dirname(__file__), "../create_bedrock_agents.py")
        role_arn = "arn:aws:iam::680038756295:role/admin"

        try:
            # Execute the Python script and pass the role_arn parameter
            result = subprocess.run(
                ["python3", python_file_path, role_arn],
                capture_output=True,
                text=True,
                check=True,
            )
            try:
                start_index = result.stdout.find("{\"final_supervisor_agent_id")
                
                if start_index == -1:
                    raise ValueError("The expected JSON key 'final_supervisor_agent_id' was not found in the output.")
                
                # Try to find the last closing brace for the JSON string
                end_index = result.stdout.rfind("}") + 1  # +1 to include the closing brace

                # Extract the JSON string
                json_str = result.stdout[start_index:end_index].strip()
                
                print("Extracted JSON string:")
                print(json_str)
                
                # Parse the JSON string
                output = json.loads(json_str)

                # Extract values from the parsed JSON
                agent_id = output.get("final_supervisor_agent_id")
                agent_alias_id = output.get("final_supervisor_agent_alias")
                
                print(f"Agent ID: {agent_id}, Agent Alias: {agent_alias_id}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON. Error: {e}")
                print(f"Raw output: {result.stdout.strip()}")
                raise
            except ValueError as ve:
                print(f"ValueError: {ve}")
                raise


            if not agent_id or not agent_alias_id:
                raise ValueError("The Python script did not return agent_id or agent_alias")

            print(f"Agent ID: {agent_id}, Agent Alias: {agent_alias_id}")

        except subprocess.CalledProcessError as e:
            print("Error executing Python file!")
            print(f"Error: {e.stderr.strip()}")

        # Get the Docker context directory
        docker_context_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # Build and push Docker image to ECR
        docker_image_asset = ecr_assets.DockerImageAsset(self, "MyDockerImage",
            directory=docker_context_path,
            platform=ecr_assets.Platform.LINUX_AMD64,
            exclude=["cdk", "cdk.out", ".git", "__pycache__", "*.pyc"]
        )

        # Create VPC
        vpc = ec2.Vpc(self, "MyVPC",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                )
            ]
        )

        # Create Security Groups
        alb_security_group = ec2.SecurityGroup(
            self, "AlbSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True
        )
        
        alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80)
        )

        service_security_group = ec2.SecurityGroup(
            self, "ServiceSecurityGroup",
            vpc=vpc,
            allow_all_outbound=True
        )

        service_security_group.add_ingress_rule(
            alb_security_group,
            ec2.Port.tcp(8501)
        )

        # Create ECS Cluster
        cluster = ecs.Cluster(self, "MyCluster", 
            vpc=vpc,
            enable_fargate_capacity_providers=True
        )

        # Create task role
        task_role = iam.Role(self, "MyTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEC2ContainerRegistryReadOnly"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )

        # Define the ECS Fargate Task Definition
        task_definition = ecs.FargateTaskDefinition(
            self, 
            "MyTaskDef",
            task_role=task_role,
            execution_role=task_role,
            cpu=512,
            memory_limit_mib=1024
        )

        # Add container with logging
        container = task_definition.add_container("MyContainer",
            image=ecs.ContainerImage.from_docker_image_asset(docker_image_asset),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="app",
                log_group=logs.LogGroup(
                    self,
                    "MyLogGroup",
                    retention=logs.RetentionDays.ONE_WEEK,
                    removal_policy=RemovalPolicy.DESTROY
                )
            ),
            environment={
                "AGENT_ID": agent_id,
                "AGENT_ALIAS_ID": agent_alias_id
            }
        )

        container.add_port_mappings(
            ecs.PortMapping(container_port=8501)
        )

        # Create ALB
        alb = elbv2.ApplicationLoadBalancer(
            self, "MyLoadBalancer",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_security_group
        )

        # Create Fargate Service
        service = ecs.FargateService(
            self, "MyFargateService",
            cluster=cluster,
            task_definition=task_definition,
            security_groups=[service_security_group],
            assign_public_ip=False,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            )
        )

        # Add listener and target group
        listener = alb.add_listener("Listener", port=80)
        listener.add_targets("ECS",
            port=8501,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service],
            health_check=elbv2.HealthCheck(
                path="/",
                healthy_http_codes="200,302",
                port="8501"  # Specify the health check port
            )
        )

        # Output ALB DNS
        CfnOutput(
            self, "LoadBalancerDNS",
            value=alb.load_balancer_dns_name
        )