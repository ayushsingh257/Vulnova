"use client";

import React, { useState } from "react";
import { Code, Copy, Check, FileCode } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export const PipelineExampleViewer: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"github" | "gitlab" | "jenkins">("github");
  const [copied, setCopied] = useState(false);

  const EXAMPLES = {
    github: `name: Vulnova CI/CD Security Pipeline Scan

on:
  push:
    branches: [ main, release/* ]
  pull_request:
    branches: [ main ]

jobs:
  vulnova-security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Vulnova CLI & Run Scan
        env:
          VULNOVA_SERVER_URL: \${{ secrets.VULNOVA_SERVER_URL }}
          VULNOVA_API_TOKEN: \${{ secrets.VULNOVA_API_TOKEN }}
        run: |
          pip install vulnova-cli
          SCAN_JSON=\$(vulnova scan start --target "\${{ github.repository }}" --project "\${{ github.repository }}" --branch "\${{ github.ref_name }}" --commit "\${{ github.sha }}" --json --quiet)
          SCAN_ID=\$(echo "\$SCAN_JSON" | jq -r '.scan_id')
          vulnova gate check --id "\$SCAN_ID" --max-critical 0 --max-high 2`,

    gitlab: `stages:
  - security

vulnova_security_scan:
  stage: security
  image: python:3.11-slim
  variables:
    VULNOVA_SERVER_URL: "https://api.vulnova.com"
    VULNOVA_API_TOKEN: "$VULNOVA_API_TOKEN"
  script:
    - pip install vulnova-cli
    - SCAN_ID=\$(vulnova scan start --target "$CI_PROJECT_PATH" --project "$CI_PROJECT_NAME" --branch "$CI_COMMIT_BRANCH" --commit "$CI_COMMIT_SHA" --json --quiet | grep -o '"scan_id": "[^"]*' | cut -d'"' -f4)
    - vulnova gate check --id "$SCAN_ID" --max-critical 0 --max-high 2
  only:
    - merge_requests
    - main`,

    jenkins: `pipeline {
    agent any

    environment {
        VULNOVA_SERVER_URL = 'https://api.vulnova.com'
        VULNOVA_API_TOKEN  = credentials('vulnova-api-token')
    }

    stages {
        stage('Vulnova Security Scan') {
            steps {
                sh '''
                    pip install vulnova-cli
                    SCAN_ID=\$(vulnova scan start --target "\${JOB_NAME}" --project "\${JOB_NAME}" --branch "\${GIT_BRANCH}" --commit "\${GIT_COMMIT}" --json --quiet | jq -r '.scan_id')
                    vulnova gate check --id "\$SCAN_ID" --max-critical 0 --max-high 2
                '''
            }
        }
    }
}`,
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(EXAMPLES[activeTab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-zinc-800">
        <div className="flex items-center space-x-2">
          <FileCode className="h-4 w-4 text-purple-400" />
          <CardTitle className="text-sm font-bold text-white">
            CI/CD Pipeline Integration Templates
          </CardTitle>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center space-x-1 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-xs text-zinc-300 hover:text-white"
        >
          {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
          <span>{copied ? "Copied" : "Copy Template"}</span>
        </button>
      </CardHeader>

      <CardContent className="pt-4 space-y-3 text-xs">
        <div className="flex space-x-2 border-b border-zinc-800 pb-2">
          <button
            onClick={() => setActiveTab("github")}
            className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
              activeTab === "github"
                ? "bg-purple-950/50 border border-purple-800/60 text-purple-300"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            GitHub Actions (.yml)
          </button>
          <button
            onClick={() => setActiveTab("gitlab")}
            className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
              activeTab === "gitlab"
                ? "bg-purple-950/50 border border-purple-800/60 text-purple-300"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            GitLab CI (.gitlab-ci.yml)
          </button>
          <button
            onClick={() => setActiveTab("jenkins")}
            className={`px-3 py-1.5 rounded-md font-semibold transition-colors ${
              activeTab === "jenkins"
                ? "bg-purple-950/50 border border-purple-800/60 text-purple-300"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Jenkins (Jenkinsfile)
          </button>
        </div>

        <pre className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 font-mono text-[11px] text-zinc-300 overflow-x-auto max-h-72">
          <code>{EXAMPLES[activeTab]}</code>
        </pre>
      </CardContent>
    </Card>
  );
};
