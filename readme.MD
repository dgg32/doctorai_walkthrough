

# Introduction

  

This repository contains code and data for my article "[Doctor.ai, an AI-Powered Virtual Voice Assistant for Health Care](https://dgg32.medium.com/doctor-ai-an-ai-powered-virtual-voice-assistant-for-health-care-8c09af65aabb)".

1. The template.yaml is for AWS SAM deployment.

  

2. Neo4j command is for data import.

  


# Prerequisite

AWS CLI and SAM

Chrome
  

# Run

## build the bundle
sam build

## deployment in AWS
sam deploy --guided --capabilities CAPABILITY_NAMED_IAM
  

## Authors

  

*  **Sixing Huang** - *Concept and Coding*
*  **Derek Ding** - *AWS management, Neo4j import and Cypher*
*  **Emil Pastor** - *AWS Lambda*
*  **Irwan Butar Butar** - *React frontend*
*  **Shiny Zhu** - *Presentation*

  

## License

  

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
