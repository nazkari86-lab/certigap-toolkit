# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM maven:3.9.11-eclipse-temurin-17 AS build

ARG YCSB_COMMIT=d9faaac85a95acd4c650a3436ac41eeaeb49c365
RUN git clone https://github.com/brianfrankcooper/YCSB.git /src/ycsb \
    && cd /src/ycsb \
    && git checkout "${YCSB_COMMIT}" \
    && mvn -pl site.ycsb:rocksdb-binding -am package -DskipTests \
    && mkdir /out \
    && tar -xzf rocksdb/target/ycsb-rocksdb-binding-*.tar.gz \
        --strip-components=1 -C /out

FROM eclipse-temurin:17-jre
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && ln -s /usr/bin/python3 /usr/local/bin/python \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /out /opt/ycsb
WORKDIR /opt/ycsb
ENTRYPOINT ["./bin/ycsb"]
