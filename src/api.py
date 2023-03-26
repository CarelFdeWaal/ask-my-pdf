from flask import Flask, request, jsonify
import uuid
import os
import prompts
import model
import storage
import feedback
import cache

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploaded_pdfs"
app.config["ALLOWED_EXTENSIONS"] = {"pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

@app.route("/api/v1/upload_pdf", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file found in request"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        #pdf_id = str(uuid.uuid4())
        pdf_id = file.filename
        # SAVE FILE HERE
        api_key = os.getenv('API_KEY','')
        db = storage.get_storage(api_key, data_dict={})
        c = cache.get_cache()
        model.use_key(api_key)
        index = model.index_file(file, pdf_id, fix_text=True, frag_size=400, cache=c)
        #index = db.get(file.filename)
        db.put(pdf_id, index)
        return jsonify({"pdf_id": pdf_id}), 201

    return jsonify({"error": "Invalid file format. Only PDF files are allowed."}), 400

@app.route("/api/v1/ask_question", methods=["POST"])
def ask_question():
    data = request.get_json()

    if not data or "pdf_id" not in data or "question" not in data:
        return jsonify({"error": "Invalid request. Please provide both 'pdf_id' and 'question' in the request body."}), 400
    api_key = os.getenv('API_KEY','')
    db = storage.get_storage(api_key, data_dict={})
    pdf_id = data["pdf_id"]
    index = db.get(pdf_id,{})
    question = data["question"]
    # PROCESS QUESTION HERE
    temperature = 0.7
    hyde = True
    hyde_prompt = prompts.HYDE
    summary = index['summary']
    hyde_prompt += f" Context: {summary}\n\n"
    task = prompts.TASK['v6']
    max_frags = 4
    n_before = 1
    n_after  = 1
    resp = model.query(question, index,
            task=task,
            temperature=temperature,
            hyde=hyde,
            hyde_prompt=hyde_prompt,
            max_frags=max_frags,
            limit=max_frags+2,
            n_before=n_before,
            n_after=n_after,
            model='gpt-3.5-turbo',
        )
  
    #q = question.strip()
    answer = resp['text'].strip()
    return jsonify({"answer": answer}), 200

if __name__ == "__main__":
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])
    app.run(host="0.0.0.0", debug=True)
