import os
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from openai import OpenAI
import threading
from datetime import datetime
import json
import re
from html import unescape

# --------------------------
# File Path
# --------------------------
INDEX_File = "./Index.txt"
Smart_File = "./AOP-Smart.json"
HISTORY_FILE = "llm_history.txt"

client = None
thinking_running = False  # Global Control Switch
llm_thread = None  # Current Running Thread
llm_running = False  # LLM currently running
thinking_index = None  # 先定义全局
# Control the number of characters in the description stage
clean_text_ke = 200
clean_text_ker = 120
clean_text_ao = 250

# thread management
current_id = 0


def load_metadata(json_file):
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            metadata = data.get("metadata", {})
            xml_date = metadata.get("xml_version", "Unknown")
            return xml_date
    except Exception as e:
        return "Load failed"


def animate_thinking():
    if not thinking_running:
        return
    global thinking_index
    dots = (animate_thinking.dots + 1) % 4
    animate_thinking.dots = dots
    text = "." * dots
    output_box.delete(thinking_index, f"{thinking_index} lineend")
    output_box.insert(thinking_index, text)
    output_box.see(tk.END)
    root.after(500, animate_thinking)


animate_thinking.dots = 0


def clean_text(text, max_len, max_sentences=2):
    if not text:
        return "-"
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    text = re.sub(r"\b[0-9A-Fa-f]{10,}\b", "", text)
    text = " ".join(text.split())
    sentences = re.split(r'(?<=[.!?]) +', text)
    text = " ".join(sentences[:max_sentences])
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0]
    return text

# --------------------------
# Initialize Client
# --------------------------
def initialize_client():
    global client

    api_key = api_key_entry.get().strip()
    base_url = base_url_entry.get().strip()

    if not api_key:
        messagebox.showerror("Error", "API key required")
        return False

    try:
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        return True

    except Exception as e:
        messagebox.showerror("Error", str(e))
        return False


# --------------------------
# Fetch model list
# --------------------------
def fetch_models():
    if not initialize_client():
        return

    api_status_var.set("API Status: Fetching models...")

    try:
        models = client.models.list()
        model_names = [m.id for m in models.data]

        model_dropdown["values"] = model_names
        if model_names:
            model_dropdown.set(model_names[0])

        api_status_var.set("API Status: OK")
        messagebox.showinfo("Models Loaded", f"Found {len(model_names)} models")

    except Exception as e:
        api_status_var.set("API Status: Error")
        messagebox.showerror("Failed", str(e))


# --------------------------
# Step 1: Get KE IDs
# --------------------------
def get_relevant_ke_ids(question, model_name, temperature, top_n):
    with open(INDEX_File, "r", encoding="utf-8") as f:
        index_data = f.read()
    global thinking_running, thinking_index
    output_box.insert(tk.END, "[LLM is thinking about which KEs to choose]")
    thinking_index = output_box.index(tk.END)
    output_box.insert(tk.END, "\n")
    thinking_running = True
    animate_thinking()
    system_prompt = f"""You are AOP-Smart, an expert system for Adverse Outcome Pathways (AOP).
Below is the index of all known Key Events (KEs).
Each line is in the format:
<KE>
id|title
id|title
id|title
...
</KE>

Task:
Given a user question, select the most relevant KE ids.
Procedure:
Stage 1 — Candidate Filtering:
1. Read all KEs and identify a broad set of potentially relevant candidates.
2. Use high recall: include any KE that is possibly related (semantic, biological, or toxicological relevance).
3. Limit this candidate set to at most 3 × {top_n} KEs.

Stage 2 — Relevance Scoring and Ranking:
4. For each candidate KE, assign a relevance score from 0 to 1:
   - 0 = completely irrelevant
   - 1 = highly relevant
5. Scoring must be based strictly on semantic and biological relevance to the question.
6. Prefer:
   - exact biological processes
   - matching pathways or mechanisms
   - specific toxicological endpoints
7. Penalize:
   - vague or generic KEs
   - weak or indirect associations

Final Selection:
8. Rank all candidate KEs by score (descending).
9. Select the top {top_n} KE ids.

Output:
Return ONLY the KE ids as a ranked list (highest relevance first), in this format:
[1,3,4,5]

Constraints:
- Do NOT output scores
- Do NOT output explanations
- Be deterministic and consistent
- If scores are similar, prefer more specific KE titles
"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{index_data}\n\nQuestion:\n{question}"}
            ],
            temperature=temperature,
            max_tokens=5000
        )

        text = response.choices[0].message.content.strip()
        thinking_running = False
        output_box.delete("1.0", tk.END)
        match = re.search(r"\[(.*?)\]", text)
        if match:
            ids = match.group(1).split(",")
            return [i.strip() for i in ids if i.strip()]

        return []

    except Exception as e:
        messagebox.showerror("KE Selection Error", str(e))
        return []


def simplify_context(selected_ke, selected_ker, selected_aop, kers, key_events):
    global clean_text_ke
    global clean_text_ker
    global clean_text_ao
    ke_entries = []
    for ke_id, ke in selected_ke.items():
        title = ke.get("title", "") or "-"
        level = ke.get("level", "") or "-"
        organ = ke.get("organ", "") or "-"
        cell = ke.get("cell", "") or "-"
        description = clean_text(ke.get("description", ""), clean_text_ke) or "-"

        applicability = ke.get("applicability", {})
        sex_list = [s.get("sex", "-") or "-" for s in applicability.get("sex", [])]
        life_stage_list = [l.get("life_stage", "-") or "-" for l in applicability.get("life_stage", [])]
        taxonomy_list = [t.get("taxonomy", "-") or "-" for t in applicability.get("taxonomy", [])]

        sex_str = ",".join(sex_list) if sex_list else "-"
        life_stage_str = ",".join(life_stage_list) if life_stage_list else "-"
        taxonomy_str = ",".join(taxonomy_list) if taxonomy_list else "-"

        app_str = f"sex:{sex_str}|life_stage:{life_stage_str}|taxonomy:{taxonomy_str}"

        ke_entry = f"[{ke_id}|{title}|{level}|{organ}|{cell}|{description}|{app_str}]"
        ke_entries.append(ke_entry)
    ke_prompt = """Below is a list of Key Events (KE) in a simplified format.
Each KE is enclosed in square brackets [] with fields separated by '|':
[id | title | level | organ | cell | description | applicability]
- id: Unique identifier of the KE (always present)
- title: Name of the KE (always present)
- level: Biological level (Molecular, Cellular, Tissue, Individual, etc.; use '-' if unknown)
- organ: Target organ or tissue (use '-' if unknown)
- cell: Cell type if applicable (use '-' if unknown)
- description: Short description of the KE (use '-' if empty)
- applicability: Information about sex, life stage, taxonomy in the format
  sex:<list> | life_stage:<list> | taxonomy:<list>
  Use '-' for each category if no information is available.\n"""
    ke_text = "\n KE:\n" + "\n".join(ke_entries) + "\n"

    ker_entries = []
    for ker_id, ker in selected_ker.items():
        upstream = ker.get("upstream_id") or "-"
        downstream = ker.get("downstream_id") or "-"
        description = clean_text(ker.get("description", ""), clean_text_ker) or "-"
        applicability = ker.get("applicability", {})
        sex_list = [s.get("sex") for s in applicability.get("sex", [])] or ["-"]
        life_stage_list = [l.get("life_stage") for l in applicability.get("life_stage", [])] or ["-"]
        taxonomy_list = [t.get("taxonomy") for t in applicability.get("taxonomy", [])] or ["-"]
        app_str = f"sex:{','.join(sex_list)}|life_stage:{','.join(life_stage_list)}|taxonomy:{','.join(taxonomy_list)}"
        ker_entry = f"[{upstream}->{downstream}|{description}|{app_str}]"
        ker_entries.append(ker_entry)
    ker_prompt = """Below is a list of Key Event Relationships (KERs) in a simplified format.
Each KER is in its own square brackets [] in the following format:
[upstream_id -> downstream_id | description | applicability]
- upstream_id: KE ID of the upstream event 
- downstream_id: KE ID of the downstream event
- description: short text describing the causal link (use '-' if none)
- applicability: information about sex, life stage, and taxonomy in the format
  sex:<list> | life_stage:<list> | taxonomy:<list> (use '-' if none)
"""
    ker_text = "\nKER:\n" + "\n".join(ker_entries)

    aop_entries = []
    for aop_id, aop in selected_aop.items():
        title = aop.get("title", "") or "-"
        abstract = clean_text(aop.get("abstract", ""), clean_text_ao) or "-"
        applicability = aop.get("applicability", {})
        sex_list = [s.get("sex", "-") for s in applicability.get("sex", [])] or ["-"]
        life_stage_list = [l.get("life_stage", "-") for l in applicability.get("life_stage", [])] or ["-"]
        taxonomy_list = [t.get("taxonomy", "-") for t in applicability.get("taxonomy", [])] or ["-"]
        app_str = f"sex:{','.join(sex_list)}|life_stage:{','.join(life_stage_list)}|taxonomy:{','.join(taxonomy_list)}"

        def format_ke_list(ids):
            formatted = []
            for ke_id in ids:
                ke_id_str = str(ke_id)
                if ke_id_str in key_events:
                    title = key_events[ke_id_str].get("title", "")
                    formatted.append(f"{ke_id_str}({title})")
                else:
                    formatted.append(ke_id_str)
            return formatted

        mie_ids = format_ke_list([m.get("key_event_id", "-") for m in aop.get("MIEs", [])] or ["-"])
        ke_ids = format_ke_list(aop.get("KEs", []) or ["-"])
        ao_ids = format_ke_list([a.get("key_event_id", "-") for a in aop.get("AOs", [])] or ["-"])

        ker_rels = []
        for kr in aop.get("KE_relationships", []):
            upstream = kers[kr["id"]].get("upstream_id", "-") or "-"
            downstream = kers[kr["id"]].get("downstream_id", "-") or "-"
            ker_rels.append(f"{upstream}->{downstream}")
        if not ker_rels:
            ker_rels = ["-"]

        aop_entry = f"[{aop_id}|{title}|{abstract}|MIEs:{','.join(mie_ids)}|KEs:{','.join(ke_ids)}|AOs:{','.join(ao_ids)}|KERs:{','.join(ker_rels)}|{app_str}]"
        aop_entries.append(aop_entry)

    aop_prompt = """
Below is a list of Adverse Outcome Pathways (AOPs) in simplified format.
Each AOP is represented in square brackets [] with fields separated by '|':
[id | title | abstract | MIEs | KEs | AOs | KERs | applicability]
Definitions:
- MIEs (Molecular Initiating Events): the starting KEs in the pathway (no upstream)
- KEs: intermediate Key Events between MIEs and AOs
- AOs (Adverse Outcomes): the ending KEs in the pathway (no downstream)
- KERs: causal relationships in the format upstream_ke_id -> downstream_ke_id
- applicability: biological applicability information:
    • sex:<list> | life_stage:<list> | taxonomy:<list>
    • '-' means not specified
    """
    aop_text = "AOP:\n" + "\n".join(aop_entries) + "\n"
    overall_prompt = """The following is an AOP knowledge base:\n
    """
    AOP_smart = overall_prompt + "<KE>\n" + ke_prompt + ke_text + "</KE>\n\n" + "<KE_relation>\n" + ker_prompt + ker_text + "\n<KE_relation>" + "\n\n<AOP>\n" + aop_prompt + aop_text + "</AOP>"
    return AOP_smart


# --------------------------
# Step 2: Construct context
# --------------------------
def build_context_from_ke_ids(ke_ids):
    with open(Smart_File, "r", encoding="utf-8") as f:
        data = json.load(f)

    key_events = data.get("key_events", {})
    kers = data.get("kers", {})
    aops = data.get("aops", {})

    selected_ke = {}
    selected_ker = {}
    selected_aop = {}

    initial_ke = set(ke_ids)

    downstream_ke = set()
    for ker_id, ker in kers.items():
        upstream = ker.get("upstream_id")
        downstream = ker.get("downstream_id")
        if upstream in initial_ke:
            downstream_ke.add(downstream)
    ke_up = set()
    for ker_id, ker in kers.items():
        up = ker.get("upstream_id")
        down = ker.get("downstream_id")
        if down in initial_ke:
            ke_up.add(up)

    expanded_ke = initial_ke.union(downstream_ke)
    expanded_ke = expanded_ke.union(ke_up)

    for aop_id, aop in aops.items():
        check = 0
        for mie in aop.get("MIEs", []):
            if mie.get("key_event_id") in expanded_ke:
                check = check + 1
        for ke in aop.get("KEs", []):
            if ke in expanded_ke:
                check = check + 1
        for ao in aop.get("AOs", []):
            if ao.get("key_event_id") in expanded_ke:
                check = check + 1
        if check >= 2:
            selected_aop[aop_id] = aop

    for ke_id in expanded_ke:
        if ke_id in key_events:
            selected_ke[ke_id] = key_events[ke_id]

    for ker_id, ker in kers.items():
        upstream = ker.get("upstream_id")
        downstream = ker.get("downstream_id")
        if upstream in expanded_ke and downstream in expanded_ke:
            selected_ker[ker_id] = ker

    context = simplify_context(selected_ke, selected_ker, selected_aop, kers, key_events)

    total_ke_count = len(key_events)
    total_ker_count = len(kers)
    total_aop_count = len(aops)

    activated_ke_count = len(selected_ke)
    activated_ker_count = len(selected_ker)
    activated_aop_count = len(selected_aop)

    ke_percent = activated_ke_count / total_ke_count * 100 if total_ke_count else 0
    ker_percent = activated_ker_count / total_ker_count * 100 if total_ker_count else 0
    aop_percent = activated_aop_count / total_aop_count * 100 if total_aop_count else 0

    context_str = json.dumps(context, ensure_ascii=False)
    word_count = len(re.findall(r'\w+', context_str))

    stats = {
        "activated_ke_count": activated_ke_count,
        "activated_ker_count": activated_ker_count,
        "activated_aop_count": activated_aop_count,
        "ke_percent": round(ke_percent, 2),
        "ker_percent": round(ker_percent, 2),
        "aop_percent": round(aop_percent, 2),
        "context_word_count": word_count
    }

    return json.dumps(context, ensure_ascii=False, indent=2), stats  # ✅ 返回 context + stats


# --------------------------
# Run LLM
# --------------------------
def run_llm_thread():
    global llm_thread, llm_running
    global current_id
    if llm_running:
        messagebox.showinfo("Info", "It is running\nDon't click repeatedly")
        return
    current_id += 1
    thread_id = current_id
    llm_thread = threading.Thread(target=run_llm, args=(thread_id,), daemon=True)
    llm_thread.start()


def reset_ui_state():
    global llm_running, thinking_running
    run_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)
    llm_running = False
    thinking_running = False


def run_llm(thread_id):
    global llm_running, thinking_running
    global current_id
    llm_running = True
    run_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    if not initialize_client():
        reset_ui_state()
        return

    task_text = task_entry.get("1.0", tk.END).strip()

    if not task_text:
        messagebox.showerror("Error", "Please enter task description")
        reset_ui_state()
        return

    model_name = model_dropdown.get()

    try:
        max_tokens = int(max_tokens_entry.get())
    except:
        max_tokens = 4096

    try:
        temperature = float(temperature_entry.get())
    except:
        temperature = 0

    try:
        top_n = int(top_n_entry.get())
    except:
        top_n = 5  # 默认 5

    output_box.config(state=tk.NORMAL)
    output_box.delete("1.0", tk.END)

    # --------------------------
    # Step 1: KE select
    # --------------------------
    ke_ids = get_relevant_ke_ids(task_text, model_name, temperature, top_n)
    if not llm_running:
        reset_ui_state()
        return
    if not ke_ids:
        messagebox.showerror("Error", "No KE found")
        reset_ui_state()
        return
    # --------------------------
    # Step 2: Construct context
    # --------------------------

    dataset, stats = build_context_from_ke_ids(ke_ids)  # 修改这里，接收 stat

    # statistical information
    stat_msg = (f"Selected KE(s): {stats['activated_ke_count']} ({stats['ke_percent']}%)\n"
                f"Selected KER(s): {stats['activated_ker_count']} ({stats['ker_percent']}%)\n"
                f"Selected AOP(s): {stats['activated_aop_count']} ({stats['aop_percent']}%)\n"
                f"Context word count: {stats['context_word_count']}")
    if not llm_running:
        reset_ui_state()
        return
    if thread_id != current_id:
        return
    # Let the user decide
    confirm = messagebox.askyesno(
        "Context Check",
        stat_msg + "\n\nDo you want to continue?"
    )

    if not confirm:
        output_box.insert(tk.END, "[Stopped by user after context check]\n")
        output_box.config(state=tk.DISABLED)
        run_button.config(state=tk.NORMAL)
        return
    global thinking_running, thinking_index
    output_box.insert(tk.END, "[LLM conducts its thinking based on the AOP knowledge base]")
    thinking_index = output_box.index(tk.END)
    output_box.insert(tk.END, "\n")
    thinking_running = True
    animate_thinking()
    # --------------------------
    # Step 3: Final reasoning（Streaming）
    # --------------------------
    result = ""

    try:
        stream = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are AOP-Smart, an AI assistant for AOP reasoning. Answer based on provided context."
                },
                {
                    "role": "user",
                    "content": f"""
<AOP_CONTEXT>
{dataset}
</AOP_CONTEXT>

<Question>
{task_text}
</Question>
"""
                }
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )

        for chunk in stream:
            if thinking_running:
                thinking_running = False
                output_box.delete("1.0", tk.END)
            if chunk.choices and chunk.choices[0].delta:
                delta = chunk.choices[0].delta

                if hasattr(delta, "content") and delta.content:
                    text = delta.content
                    result += text

                    output_box.insert(tk.END, text)
                    output_box.see(tk.END)
                    root.update()

    except Exception as e:
        messagebox.showerror("API Error", str(e))
        run_button.config(state=tk.NORMAL)
        return

    output_box.config(state=tk.DISABLED)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(timestamp + "\n")
        f.write("Model: " + model_name + "\n\n")
        f.write("Task:\n" + task_text + "\n\n")
        f.write("KE IDs:\n" + str(ke_ids) + "\n\n")
        f.write("Result:\n" + result + "\n\n")

    run_button.config(state=tk.NORMAL)
    llm_running = False
    thinking_running = False
    run_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)


def stop_llm():
    global thinking_running, llm_running
    if not llm_running:
        return
    thinking_running = False
    llm_running = False
    output_box.insert(tk.END, "\n[Stopped by user]\n")
    output_box.config(state=tk.DISABLED)
    run_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)


# --------------------------
# GUI
# --------------------------
root = tk.Tk()
root.title("AOP-Smart")
root.geometry("1200x750")

api_status_var = tk.StringVar(value="API Status: Not Connected")

status_frame = tk.Frame(root)
status_frame.pack(fill="x", padx=10, pady=5)

tk.Label(status_frame, textvariable=api_status_var).pack(side="left")
tk.Button(
    status_frame,
    text="Fetch Models",
    command=lambda: threading.Thread(target=fetch_models, daemon=True).start()
).pack(side="left", padx=5)

config_frame = tk.LabelFrame(root, text="API Config", padx=10, pady=10)
config_frame.pack(side="left", fill="y", padx=5, pady=5)

config_frame.columnconfigure(0, minsize=120)
config_frame.columnconfigure(1, weight=1)

tk.Label(config_frame, text="Base URL").grid(row=0, column=0, sticky="w", pady=2)
base_url_entry = tk.Entry(config_frame)
base_url_entry.insert(0, "https://api.deepseek.com")
base_url_entry.grid(row=0, column=1, sticky="ew", pady=2)

tk.Label(config_frame, text="API Key").grid(row=1, column=0, sticky="w", pady=2)
api_key_entry = tk.Entry(config_frame)
api_key_entry.grid(row=1, column=1, sticky="ew", pady=2)

tk.Label(config_frame, text="Model").grid(row=2, column=0, sticky="w", pady=2)
model_dropdown = ttk.Combobox(config_frame)
model_dropdown.grid(row=2, column=1, sticky="ew", pady=2)

tk.Label(config_frame, text="Max Output").grid(row=3, column=0, sticky="w", pady=2)
max_tokens_entry = tk.Entry(config_frame)
max_tokens_entry.insert(0, "4096")
max_tokens_entry.grid(row=3, column=1, sticky="ew", pady=2)

tk.Label(config_frame, text="Temperature").grid(row=4, column=0, sticky="w", pady=2)
temperature_entry = tk.Entry(config_frame)
temperature_entry.insert(0, "0")
temperature_entry.grid(row=4, column=1, sticky="ew", pady=2)

tk.Label(config_frame, text="Top N KEs").grid(row=5, column=0, sticky="w", pady=2)
top_n_entry = tk.Entry(config_frame)
top_n_entry.insert(0, "5")
top_n_entry.grid(row=5, column=1, sticky="ew", pady=2)

parameter_describe = """Max Output: Limits the maximum number of characters the AI can generate.

Temperature: Controls the stability of the AI output.
A value of 0 provides the most stable results.
Higher values make the output more creative.
In general, setting it to 0 ensures more consistent results.

Top N KEs: This RAG system first provides the LLM with only the titles and IDs of all KEs.
Based on the user's question, the LLM automatically selects the top N most relevant KEs.
The system then expands related KE, KER, and AOP information.
It also displays the percentage of activated KEs, KERs, and AOPs.
The user can then decide whether to continue the output process.
"""
tk.Label(config_frame, text="XML Version").grid(row=6, column=0, sticky="w", pady=2)
version_label = tk.Label(config_frame, text="Loading...")
version_label.grid(row=6, column=1, sticky="w", pady=2)

tk.Label(config_frame, text=parameter_describe, fg="gray", justify="left").grid(
    row=7, column=0, columnspan=2, sticky="w", pady=2
)

right_frame = tk.Frame(root)
right_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

right_frame.grid_rowconfigure(0, weight=0)
right_frame.grid_rowconfigure(1, weight=6)
right_frame.grid_rowconfigure(2, weight=2)
right_frame.grid_columnconfigure(0, weight=1)

tk.Label(right_frame, text="Output").grid(row=0, column=0, sticky="w", pady=(0, 5))

output_box = scrolledtext.ScrolledText(
    right_frame,
    state=tk.DISABLED
)
output_box.grid(
    row=1,
    column=0,
    sticky="nsew",
    pady=(0, 10)
)

task_frame = tk.Frame(right_frame)
task_frame.grid(row=2, column=0, sticky="nsew")

task_frame.grid_columnconfigure(0, weight=1)
task_frame.grid_rowconfigure(1, weight=1)
task_frame.grid_rowconfigure(2, weight=0)

tk.Label(task_frame, text="Task").grid(row=0, column=0, sticky="w", columnspan=2)

task_entry = scrolledtext.ScrolledText(task_frame, height=5, )
task_entry.grid(
    row=1,
    column=0,
    sticky="nsew",
    padx=(0, 10),
    pady=(5, 0)
)

button_frame = tk.Frame(task_frame)
button_frame.grid(row=1, column=1, rowspan=2, sticky="n")

run_button = tk.Button(
    button_frame,
    text="Run",
    command=run_llm_thread,
    bg="#4CAF50",
    fg="white",
    width=10
)
run_button.pack(pady=(5, 5))

stop_button = tk.Button(
    button_frame,
    text="Stop",
    command=stop_llm,
    bg="#f44336",
    fg="white",
    width=10,
    state=tk.DISABLED
)
stop_button.pack()

xml_date = load_metadata("AOP-Smart.json")
version_label.config(text=xml_date)

root.mainloop()
