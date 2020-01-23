FROM neo4j:3.5.4
LABEL maintainer="patrick@covar.com"

RUN apk --no-cache add openjdk11 --repository=http://dl-cdn.alpinelinux.org/alpine/edge/community
ENV APOC_URI https://github.com/neo4j-contrib/neo4j-apoc-procedures/releases/download/3.5.0.2/apoc-3.5.0.2-all.jar
ENV ROBOKOP_URI https://github.com/NCATS-Gamma/robokop-neo4j-plugin/releases/download/v2.0.0/robokop-2.0.0.jar

RUN mkdir /plugins

RUN wget $APOC_URI \
    && mv apoc-3.5.0.2-all.jar /plugins

RUN wget $ROBOKOP_URI \
    && mv robokop-2.0.0.jar /plugins

EXPOSE 7474 7473 7687

CMD ["neo4j"]