# Edgerun FaaS

This project aims to provide a clear defined API that offers ways of interacting with a FaaS platform (i.e., deploy function)
and expose runtime metrics (i.e., recent invocations) to develop strategies on managing function deployments (i.e., scaling).

EdgeRun aims to offer two different (ready-to-use) implementations that stem from completely different backgrounds:
1. [galileo-faas](https://github.com/edgerun/galileo-faas): implements this project for a real-world testbed based on Kubernetes and [galileo-experiments](https://github.com/edgerun/galileo-experiments).
3. [faas-sim](https://github.com/edgerun/faas-sim): offers a trace-driven, event-based simulation for FaaS.

Use cases
=========
The main use case of this project is to clearly define our vision of (1) interacting with a FaaS platform and (2) exposing
runtime metrics to develop novel system components that revolve around scaling, scheduling and load balancing. 

This translates to the following concrete use cases:
* You want to deploy, shutdown and invoke a running FaaS platform (with `FaaSSystem`) 
* You want to implement a scaling/scheduling or load balancing solution that uses runtime metrics (with `PlatformContext`)

