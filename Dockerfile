# Container image for the Lambda pipeline.
# The same image can run the CLI locally by overriding the entrypoint:
#
#   docker build -t weather-etl .
#   docker run --rm --entrypoint python \
#     -v "$PWD/data:/var/task/data" \
#     -e STORAGE_BACKEND=local \
#     -e LOCAL_DATA_DIR=/var/task/data \
#     weather-etl -m weather_etl run
#
# CI does not build or push this image, and nothing here contacts AWS.

FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

COPY src/weather_etl ${LAMBDA_TASK_ROOT}/weather_etl

CMD ["weather_etl.lambda_handler.handler"]
