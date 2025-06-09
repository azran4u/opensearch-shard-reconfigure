python3.12 -m venv venv
source venv/bin/activate
python3.12 -m pip install -r requirements.txt

echo "created and activated virtual environment"

echo "reading elasticsearch-params secret"
opensearch_params=$(kubectl -n digi get secret elasticsearch-params -o json | jq -r '.data | to_entries[] | select(.key | test("elasticsearch.properties")) | .value' | base64 --decode)

es_host=$(echo "$opensearch_params" | grep 'es.host' | awk -F '=' '{gsub(/^ +| +$/, "", $2); print $2}')

if [ -z "$es_host" ] ; then
    echo "missing opensearch url in elasticsearch-params secret"
    exit 1
fi

echo "es_host: $es_host"

echo "exporting database variables"
export ELASTICSEARCH_URL=$es_host

python3.12 main.py