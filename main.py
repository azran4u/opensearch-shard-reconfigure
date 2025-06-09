#!/usr/bin/env python3
# filepath: /home/ubuntu/performance-testing/template_updater.py

import subprocess
import json
import time
import sys
import os


# OpenSearch cluster URL
elasticsearch_url = "https://vpc-alero-qa-1-l32rqdjyd567ba76iimggxmmom.us-east-1.es.amazonaws.com"
source_template = "audit-v1"
target_template = "sharding_test_template"
template_to_change = [target_template]

def opensearch_url():
    return os.environ.get('ELASTICSEARCH_URL', elasticsearch_url)

def run_command(command, parse_json=True):
    """Execute a shell command and return the result as parsed JSON or raw output"""
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    if parse_json:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON: {result.stdout}")
            return None
    return result.stdout

def opensearch_command(method, endpoint, data=None):
    """Run a command against the OpenSearch cluster"""
    command = ["curl", "-s", "-X", method, f"{elasticsearch_url}/{endpoint}", "-H", "Content-Type: application/json"]
    if data:
        command.extend(["-d", json.dumps(data)])
    
    return run_command(command)

def get_templates():
    """Retrieve all index templates from the cluster"""
    print("Retrieving templates...")
    return opensearch_command("GET", "_template")
    
def get_template_details(templates):
    """Extract template names and shard/replica settings"""
    template_details = []
    
    for template_name, template_data in templates.items():
        try:
            settings = template_data.get('settings', {}).get('index', {})
            shards = settings.get('number_of_shards', 'default')
            replicas = settings.get('number_of_replicas', 'default')
            
            # Get pattern for test document creation
            if 'index_patterns' in template_data:
                pattern = template_data['index_patterns'][0].replace('*', '_test')
            else:
                pattern = f"{template_name}_test"
                
            template_details.append({
                'name': template_name,
                'shards': shards,
                'replicas': replicas,
                'test_index': pattern
            })
        except Exception as e:
            print(f"Error processing template {template_name}: {e}")
    
    return template_details

def update_template(template_name, shards=1, replicas=1):
    """Update a template to use specified shard and replica counts"""
    print(f"Updating template {template_name} to {shards} shard(s) and {replicas} replica(s)...")
    
    # First, get the current template configuration
    current_template = opensearch_command("GET", f"_template/{template_name}", None)

    if not current_template or template_name not in current_template:
        print(f"Failed to retrieve template {template_name}")
        return False
    
    # Modify the settings
    template_config = current_template[template_name]
    if 'settings' not in template_config:
        template_config['settings'] = {}
    if 'index' not in template_config['settings']:
        template_config['settings']['index'] = {}
        
    template_config['settings']['index']['number_of_shards'] = str(shards)
    template_config['settings']['index']['number_of_replicas'] = str(replicas)
    
    # Save the updated template
    response = opensearch_command("PUT", f"_template/{template_name}", template_config)
    
    success = response and response.get('acknowledged', False)
    if success:
        print(f"Successfully updated template {template_name}")
    else:
        print(f"Failed to update template {template_name}: {response}")
    
    return success

def create_test_document(index_name):
    """Create a test document for the specified index"""
    print(f"Creating test document in index {index_name}...")
    
    # Create a document with timestamp to make it unique
    timestamp = int(time.time())
    doc = {
        "test_field": "test_value",
        "timestamp": timestamp,
        "description": "Test document for template validation"
    }
    
    response = opensearch_command("POST", f"{index_name}/_doc", doc)
    
    success = response and 'result' in response and response['result'] in ['created', 'updated']
    
    if success:
        print(f"Successfully created test document in {index_name}")
    else:
        print(f"Failed to create test document in {index_name}: {response}")
    
    return success

def verify_index_settings(index_name, expected_shards=1, expected_replicas=1):
    """Verify that an index has the expected shard and replica counts"""
    print(f"Verifying settings for index {index_name}...")
    
    response = opensearch_command("GET", f"{index_name}/_settings", None)
    
    if not response or index_name not in response:
        print(f"Failed to retrieve settings for index {index_name}")
        return False
    
    settings = response[index_name].get('settings', {}).get('index', {})
    actual_shards = int(settings.get('number_of_shards', '-1'))
    actual_replicas = int(settings.get('number_of_replicas', '-1'))
    
    if actual_shards == expected_shards and actual_replicas == expected_replicas:
        print(f"Index {index_name} has correct settings: {actual_shards} shard(s) and {actual_replicas} replica(s)")
        return True
    else:
        print(f"Index {index_name} has incorrect settings: {actual_shards} shard(s) and {actual_replicas} replica(s)")
        return False

def delete_index(index_name):
    """Delete an index"""
    print(f"Deleting index {index_name}...")

    response = opensearch_command("DELETE", index_name, None)
    
    success = response and response.get('acknowledged', False)
    
    if success:
        print(f"Successfully deleted index {index_name}")
    else:
        print(f"Failed to delete index {index_name}: {response}")
    
    return success

def copy_template(source_template, target_template):
    """Copy settings from one template to another"""
    print(f"Copying settings from {source_template} to {target_template}...")
    
    source_template_data = opensearch_command("GET", f"_template/{source_template}", None)

    if not source_template_data or source_template not in source_template_data:
        print(f"Failed to retrieve source template {source_template}")
        return False
    
    target_template_data = source_template_data[source_template]
    target_template_data['order'] = 0  # Set the template name
    target_template_data['version'] = 1  # Reset version to default
    target_template_data['index_patterns'] = [target_template + "*"]  # Set the target template name

    # Update the target template with the source template's settings
    response = opensearch_command("PUT", f"_template/{target_template}", target_template_data)
    
    success = response and response.get('acknowledged', False)
    
    if success:
        print(f"Successfully copied settings to {target_template}")
    else:
        print(f"Failed to copy settings to {target_template}: {response}")
    
    return success

def main():

    # copy_template(source_template, target_template)

    print("OpenSearch Template Management Tool")
    print("=================================\n")
    
    try:
        # Step 1: Get all templates and their details
        templates = get_templates()
        if not templates:
            print("No templates found or error retrieving templates")
            return

        # filter templates to those who start with one of the specified names in template_to_change
        templates = {k: v for k, v in templates.items() if k in template_to_change}
        
        template_details = get_template_details(templates)
        
        # Display template information
        print("\nCurrent Templates:")
        print("-----------------")
        for idx, template in enumerate(template_details, 1):
            print(f"{idx}. {template['name']}")
            print(f"   Shards: {template['shards']}")
            print(f"   Replicas: {template['replicas']}")
            print(f"   Test index: {template['test_index']}")
        
        # Ask for confirmation before proceeding
        proceed = input("\nUpdate all templates to 1 shard and 1 replica? (y/n): ")
        if proceed.lower() != 'y':
            print("Operation canceled")
            return
        
        # Step 2: Update templates
        updated_templates = []
        failed_templates = []
        
        for template in template_details:
            if update_template(template['name'], shards=1, replicas=1):
                updated_templates.append(template)
            else:
                failed_templates.append(template)
        
        # Step 3: Test the updated templates
        print("\nTesting updated templates...")
        print("---------------------------")
        
        for template in updated_templates:
            test_index = template['test_index']
            
            # Create a test document to trigger index creation
            if create_test_document(test_index):
                # Wait a moment for the index to be created with settings
                time.sleep(2)
                
                # Verify the settings
                verified = verify_index_settings(test_index, 1, 1)
                
                # Clean up by deleting the test index
                delete_index(test_index)
                
                if verified:
                    print(f"Template {template['name']} was successfully updated and verified\n")
                else:
                    print(f"Template {template['name']} was updated but verification failed\n")
            else:
                print(f"Failed to test template {template['name']}\n")
        
        # Summary
        print("\nSummary:")
        print("--------")
        print(f"Templates updated: {len(updated_templates)}/{len(template_details)}")
        
        if failed_templates:
            print("\nFailed templates:")
            for template in failed_templates:
                print(f"- {template['name']}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())