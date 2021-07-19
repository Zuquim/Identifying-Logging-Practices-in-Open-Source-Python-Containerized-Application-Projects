# Identifying Logging Practices in Open Source Python Containerized Application Projects
In Brazilian Symposium on Software Engineering (SBES ’21), Septem-ber 27-October 1, 2021, Joinville, Brazil.

## Authors
- [Marco Túlio Resende Zuquim Alves](https://github.com/Zuquim)
- [Hugo Bastos de Paula](https://github.com/hugodepaula)

## DOI
[`10.1145/3474624.3474631`](https://doi.org/10.1145/3474624.3474631)

## Abstract
  Nowadays, many software projects have migrated from the monolithic to microservice architectures by using container based virtualization.
  However, there are not many studies that describe how observability practices are being employed in this scenario.
  Since logging is the most straightforward practice among the observability pillars, it is interesting to know its current adoption level and common practices.
  In this empirical study, we cloned 10,918 of the most stargazed GitHub Python repositories with at least one Docker/Kubernetes associated file.
  Our goal is to understand what is the adoption level of observability by trying to identify popular logging practices in the community that use Docker containers.
  We were able to find 1,166 projects fitting our research requirements.
  A custom parser with regular expressions identified and saved logger statements from Python source code.
  We discovered that projects adopting certain licenses tend to have a higher logger statements/LLOC ratio.
  Other discoveries include, but are not limited to: over 99% of Python open source projects using Docker use the built-in logging library exclusively or in parallel with another one; the repository age does not affect its logger statements/LLOC ratio significantly; logging verbosity levels *debug* and *info* are used almost twice as much as *warning* and *error*.
  We hope our study provides the community with useful data about this topic, possibly contributing to the improvement of techniques that stimulate its applications.