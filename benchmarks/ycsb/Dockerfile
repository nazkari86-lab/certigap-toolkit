FROM maven:3.9.11-eclipse-temurin-17 AS build

ARG YCSB_COMMIT=d9faaac85a95acd4c650a3436ac41eeaeb49c365
RUN git clone https://github.com/brianfrankcooper/YCSB.git /src/ycsb \
    && cd /src/ycsb \
    && git checkout "${YCSB_COMMIT}" \
    && mvn -pl site.ycsb:rocksdb-binding -am package -DskipTests

FROM eclipse-temurin:17-jre
COPY --from=build /src/ycsb /opt/ycsb
WORKDIR /opt/ycsb
ENTRYPOINT ["./bin/ycsb"]
