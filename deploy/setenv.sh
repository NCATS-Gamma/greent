DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export ROBOKOP_HOME="$DIR/../.."
if [ "$DEPLOY" != "docker" ]; then
    export $(cat $ROBOKOP_HOME/shared/robokop.env | grep -v ^# | xargs)
fi

export PYTHONPATH=$ROBOKOP_HOME/robokop-interfaces
export CELERY_BROKER_URL="amqp://$BROKER_USER:$BROKER_PASSWORD@$BROKER_HOST:$BROKER_PORT/builder"
export CELERY_RESULT_BACKEND="redis://$RESULTS_HOST:$RESULTS_PORT/$BUILDER_RESULTS_DB"
export FLOWER_BROKER_API="http://admin:$ADMIN_PASSWORD@$BROKER_HOST:15672/api/"
export FLOWER_PORT="$BUILDER_FLOWER_PORT"
export FLOWER_BASIC_AUTH=${FLOWER_USER}:${FLOWER_PASSWORD}
export SUPERVISOR_PORT=$BUILDER_SUPERVISOR_PORT

# for greent conf
export TRANSLATOR_SERVICES_ROSETTAGRAPH_URL="bolt://$NEO4J_HOST:$NEO4J_BOLT_PORT"
export TRANSLATOR_SERVICES_ROSETTAGRAPH_NEO4J_PASSWORD="$NEO4J_PASSWORD"
#These get exported by robokop.env?
export REDIS_HOST="$CACHE_HOST"
export REDIS_PORT="$CACHE_PORT"
export REDIS_DB="$CACHE_DB"
