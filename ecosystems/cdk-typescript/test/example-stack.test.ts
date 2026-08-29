import * as cdk from "aws-cdk-lib";
import { Template } from "aws-cdk-lib/assertions";
import { ExampleStack } from "../lib/example-stack";

describe("ExampleStack", () => {
  const app = new cdk.App();
  const stack = new ExampleStack(app, "TestStack");
  const template = Template.fromStack(stack);

  test("creates an SQS queue", () => {
    template.resourceCountIs("AWS::SQS::Queue", 1);
  });

  test("queue has encryption enabled", () => {
    template.hasResourceProperties("AWS::SQS::Queue", {
      SqsManagedSseEnabled: true,
    });
  });

  test("queue retention is 14 days", () => {
    template.hasResourceProperties("AWS::SQS::Queue", {
      MessageRetentionPeriod: 1209600, // 14 days in seconds
    });
  });
});
