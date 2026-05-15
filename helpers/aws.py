import boto3
import json
from time import sleep
from botocore.exceptions import ClientError


def load_file_to_s3(filename, s3_bucket, s3_key):
    print(f"Uploading data to S3://{s3_bucket}/{s3_key}")
    s3 = boto3.client('s3')
    s3.upload_file(filename, s3_bucket, s3_key)


def load_json_from_s3(s3_bucket, s3_key):
    try:
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=s3_bucket, Key=s3_key)
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        raise


def query_athena(sql, database, results_bucket, wait_seconds=60):
    athena = boto3.client('athena')

    query_start = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={'Database': database},
        ResultConfiguration={'OutputLocation': f"s3://{results_bucket}/Unsaved/"}
    )
    execution_id = query_start['QueryExecutionId']

    for _ in range(wait_seconds):
        execution = athena.get_query_execution(QueryExecutionId=execution_id)
        state = execution['QueryExecution']['Status']['State']
        if state == 'FAILED':
            raise Exception(execution['QueryExecution']['Status']['StateChangeReason'])
        elif state == 'SUCCEEDED':
            break
        sleep(1)
    else:
        raise Exception(f"Query timed out after {wait_seconds} seconds")

    results = athena.get_query_results(QueryExecutionId=execution_id)
    all_rows = results['ResultSet']['Rows']
    while 'NextToken' in results:
        results = athena.get_query_results(
            QueryExecutionId=execution_id,
            NextToken=results['NextToken']
        )
        all_rows.extend(results['ResultSet']['Rows'])

    headers = [col['VarCharValue'] for col in all_rows[0]['Data']]
    return [
        {headers[i]: col.get('VarCharValue') for i, col in enumerate(row['Data'])}
        for row in all_rows[1:]
    ]


def add_glue_partition_for(year, month, day, table, database, results_bucket):
    sql = f"ALTER TABLE {table} ADD IF NOT EXISTS PARTITION (year='{year}', month='{month}', day='{day}')"
    _execute_athena_command(sql, database, results_bucket)


def add_glue_partition_y(year, table, database, results_bucket):
    sql = f"ALTER TABLE {table} ADD IF NOT EXISTS PARTITION (year='{year}')"
    _execute_athena_command(sql, database, results_bucket)


def add_glue_partition_area(postcode_area, table, database, results_bucket):
    sql = f"ALTER TABLE {table} ADD IF NOT EXISTS PARTITION (postcode_area='{postcode_area}')"
    _execute_athena_command(sql, database, results_bucket)


def add_glue_partition_en(grid_e, grid_n, table, database, results_bucket):
    sql = f"ALTER TABLE {table} ADD IF NOT EXISTS PARTITION (grid_e='{grid_e}', grid_n='{grid_n}')"
    _execute_athena_command(sql, database, results_bucket)


def _execute_athena_command(sql, database, results_bucket, wait_seconds=10):
    athena = boto3.client('athena')
    print(f"Executing: {sql}")

    query_start = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={'Database': database},
        ResultConfiguration={'OutputLocation': f"s3://{results_bucket}/Unsaved/"}
    )

    for _ in range(wait_seconds):
        query_execution = athena.get_query_execution(QueryExecutionId=query_start['QueryExecutionId'])
        state = query_execution.get('QueryExecution', {}).get('Status', {}).get('State')

        if state == 'FAILED':
            reason = query_execution.get('QueryExecution', {}).get('Status', {}).get('StateChangeReason')
            print(f"Query failed: {reason}")
            return False
        elif state == 'SUCCEEDED':
            print('Query succeeded')
            return True

        sleep(1)

    print(f"Query timed out after {wait_seconds} seconds")
    return False
