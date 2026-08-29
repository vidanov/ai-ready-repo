#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { Aspects } from "aws-cdk-lib";
import { AwsSolutionsChecks } from "cdk-nag";
import { ExampleStack } from "../lib/example-stack";

const app = new cdk.App();

// All stacks get cdk-nag checks. See ADR-CDK-001.
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));

new ExampleStack(app, "ExampleStack", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "eu-central-1",
  },
});
