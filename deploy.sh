IMAGE_NAME="ramayanquiz"
CONTAINER_BLUE="ramayanquiz-blue"
CONTAINER_GREEN="ramayanquiz-green"

function deploy_green() {
    echo "Building image"
    docker build -t $IMAGE_NAME .
    echo "Built image"

    # The blue container could be mapped to either port 8000 or 8001 on the host
    # The green container has to be mapped to the other port
    echo "Extracting blue container port"
    CONTAINER_BLUE_PORT=$(docker port $CONTAINER_BLUE | awk -F'[: ]+' '/->/ {print $NF}' | head -n 1)
    echo "Blue container port: $CONTAINER_BLUE_PORT"
    if [ "$CONTAINER_BLUE_PORT" = "8000" ]; then
        CONTAINER_GREEN_PORT="8001"
    else
        CONTAINER_GREEN_PORT="8000"
    fi
    echo "Green container port: $CONTAINER_GREEN_PORT"

    echo "Starting green container"
    docker run -d --name $CONTAINER_GREEN -v .:/app -p $CONTAINER_GREEN_PORT:8000 $IMAGE_NAME
    echo "Started green container"

    echo "Both blue and green containers are running. Switch traffic to green, i.e port $CONTAINER_GREEN_PORT, in the Load Balancer and remove the blue container."
}

function remove_blue() {
    # In addition to removing blue, it also promotes/renames green to blue.
    # This is a readiness step for the next deployment
    echo "Stopping and removing blue container."
    docker stop $CONTAINER_BLUE && docker rm $CONTAINER_BLUE
    echo "Renaming green container to blue."
    docker rename $CONTAINER_GREEN $CONTAINER_BLUE
}

if [ "$1" == "deploy" ] || [ "$1" == "" ]; then
    deploy_green
elif [ "$1" == "switch" ]; then
    remove_blue
else
    echo "Invalid argument to the deployment script"
fi
