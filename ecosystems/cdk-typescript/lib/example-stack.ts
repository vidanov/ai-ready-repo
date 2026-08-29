import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as sqs from "aws-cdk-lib/aws-sqs";
import { NagSuppressions } from "cdk-nag";

/**
 * Example stack demonstrating AI-ready CDK patterns.
 *
 * Replace with your actual infrastructure. The patterns to preserve:
 * - cdk-nag Aspects (applied in bin/app.ts, see ADR-CDK-001)
 * - Parameterized stack name (never hardcoded)
 * - No sensitive values in CfnOutput
 */
export class ExampleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Example resource: SQS queue with encryption
    const queue = new sqs.Queue(this, "ExampleQueue", {
      encryption: sqs.QueueEncryption.SQS_MANAGED,
      retentionPeriod: cdk.Duration.days(14),
      visibilityTimeout: cdk.Duration.seconds(300),
    });

    // Suppress known cdk-nag findings with justification
    NagSuppressions.addResourceSuppressions(queue, [
      {
        id: "AwsSolutions-SQS3",
        reason:
          "Dead letter queue not required for this example. Add DLQ for production use.",
      },
    ]);
  }
}
