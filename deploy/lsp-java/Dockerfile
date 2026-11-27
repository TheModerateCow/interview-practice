# Eclipse JDT language server 1.61.0 on the runner's JDK. Built at install, offline at run time. The checksum pins the tarball.
FROM eclipse-temurin:21.0.13.1_2-jdk
ADD --checksum=sha256:338e7e73d61836651ba2453919a0d34fa763eb4e7c03342092309bffb8934c64 https://download.eclipse.org/jdtls/milestones/1.61.0/jdt-language-server-1.61.0-202609031315.tar.gz /tmp/jdtls.tgz
RUN mkdir /opt/jdtls && tar xzf /tmp/jdtls.tgz -C /opt/jdtls && rm /tmp/jdtls.tgz
