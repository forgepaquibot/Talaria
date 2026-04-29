from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/function', methods=['POST'])
def my_function():
    data = request.json
    # Call your Python function here
    result = some_python_function(data['input'])
    return jsonify({'result': result})

def some_python_function(input_data):
    # Example function logic
    return f"Processed: {input_data}"

if __name__ == '__main__':
    app.run(debug=True)
