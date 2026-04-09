import streamlit as st
import sys
import io
import traceback
import time
import textwrap
from contextlib import redirect_stdout, redirect_stderr

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Python Learning Window",
    page_icon="🐍",
    layout="wide",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark header bar */
    .header-bar {
        background: linear-gradient(135deg, #1e1e2e 0%, #313244 100%);
        padding: 18px 24px;
        border-radius: 12px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .header-bar h1 { color: #cdd6f4; margin: 0; font-size: 1.6rem; }
    .header-bar span { font-size: 2rem; }

    /* Editor window */
    .editor-label {
        background: #1e1e2e;
        color: #89b4fa;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 6px 14px;
        border-radius: 8px 8px 0 0;
        display: inline-block;
        letter-spacing: 0.5px;
    }

    /* Output box */
    .output-box {
        background: #1e1e2e;
        border: 1.5px solid #313244;
        border-radius: 0 8px 8px 8px;
        padding: 16px;
        font-family: 'Fira Code', 'Courier New', monospace;
        font-size: 0.88rem;
        min-height: 180px;
        white-space: pre-wrap;
        word-break: break-word;
    }
    .output-success { color: #a6e3a1; }
    .output-error   { color: #f38ba8; }
    .output-empty   { color: #585b70; font-style: italic; }

    /* Stats pills */
    .stat-pill {
        display: inline-block;
        background: #313244;
        color: #cdd6f4;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.78rem;
        margin-right: 8px;
    }
    .stat-ok   { background: #1e3a2f; color: #a6e3a1; }
    .stat-err  { background: #3b1e28; color: #f38ba8; }

    /* Snippet cards */
    .snippet-card {
        background: #181825;
        border: 1px solid #313244;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
        cursor: pointer;
    }
    .snippet-title { color: #89dceb; font-weight: 600; font-size: 0.9rem; }
    .snippet-desc  { color: #9399b2; font-size: 0.80rem; margin-top: 3px; }

    /* Sidebar tweaks */
    section[data-testid="stSidebar"] { background: #181825; }
    section[data-testid="stSidebar"] * { color: #cdd6f4 !important; }

    /* Run button override */
    div.stButton > button {
        background: linear-gradient(135deg, #89b4fa, #b4befe);
        color: #1e1e2e;
        font-weight: 700;
        border: none;
        border-radius: 8px;
        padding: 10px 28px;
        font-size: 0.95rem;
        transition: opacity 0.2s;
    }
    div.stButton > button:hover { opacity: 0.85; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []          # list of {code, output, ok, ms}
if "persistent_env" not in st.session_state:
    st.session_state.persistent_env = {}   # shared exec namespace
if "code" not in st.session_state:
    st.session_state.code = '# 👋 Welcome! Write your Python code here\nprint("Hello, World!")'

# ── Snippet library ────────────────────────────────────────────────────────────
SNIPPETS = {
    "🔢 Variables & Types": {
        "desc": "Integers, floats, strings, booleans",
        "code": textwrap.dedent("""\
            name   = "Alice"
            age    = 25
            height = 5.6
            active = True

            print(f"Name   : {name}  ({type(name).__name__})")
            print(f"Age    : {age}   ({type(age).__name__})")
            print(f"Height : {height} ({type(height).__name__})")
            print(f"Active : {active} ({type(active).__name__})")
        """)
    },
    "📋 Lists & Loops": {
        "desc": "List creation, iteration, comprehension",
        "code": textwrap.dedent("""\
            fruits = ["apple", "banana", "cherry", "date"]

            print("── for loop ──")
            for i, fruit in enumerate(fruits, 1):
                print(f"  {i}. {fruit}")

            print("── list comprehension ──")
            upper = [f.upper() for f in fruits]
            print(upper)
        """)
    },
    "🔄 Functions": {
        "desc": "def, return, default args, *args",
        "code": textwrap.dedent("""\
            def greet(name, greeting="Hello"):
                return f"{greeting}, {name}!"

            def add(*numbers):
                return sum(numbers)

            print(greet("Bob"))
            print(greet("Alice", "Hi"))
            print("Sum:", add(1, 2, 3, 4, 5))
        """)
    },
    "🏗️ Classes (OOP)": {
        "desc": "Class, __init__, methods, inheritance",
        "code": textwrap.dedent("""\
            class Animal:
                def __init__(self, name, sound):
                    self.name  = name
                    self.sound = sound

                def speak(self):
                    return f"{self.name} says {self.sound}!"

            class Dog(Animal):
                def __init__(self, name):
                    super().__init__(name, "Woof")

                def fetch(self):
                    return f"{self.name} fetches the ball! 🎾"

            dog = Dog("Rex")
            print(dog.speak())
            print(dog.fetch())
        """)
    },
    "⚠️ Error Handling": {
        "desc": "try / except / finally blocks",
        "code": textwrap.dedent("""\
            def safe_divide(a, b):
                try:
                    result = a / b
                except ZeroDivisionError:
                    return "Error: cannot divide by zero!"
                except TypeError as e:
                    return f"Type error: {e}"
                else:
                    return f"{a} / {b} = {result}"
                finally:
                    print("  (division attempted)")

            print(safe_divide(10, 2))
            print(safe_divide(10, 0))
            print(safe_divide(10, "x"))
        """)
    },
    "🗂️ Dictionaries": {
        "desc": "Create, access, iterate, comprehension",
        "code": textwrap.dedent("""\
            student = {
                "name": "Alice",
                "grade": "A",
                "scores": [95, 88, 92]
            }

            print("Name :", student["name"])
            print("Avg  :", sum(student["scores"]) / len(student["scores"]))

            # dict comprehension
            squares = {n: n**2 for n in range(1, 6)}
            print("Squares:", squares)
        """)
    },
    "📦 Modules (math/random)": {
        "desc": "Import built-in modules",
        "code": textwrap.dedent("""\
            import math
            import random

            print("π     =", math.pi)
            print("√2    =", math.sqrt(2))
            print("log10 =", math.log10(1000))

            print("\\nRandom integers:", [random.randint(1, 10) for _ in range(5)])
            print("Shuffled list   :", end=" ")
            lst = list(range(1, 6)); random.shuffle(lst); print(lst)
        """)
    },
    "📝 String Methods": {
        "desc": "Common string operations",
        "code": textwrap.dedent("""\
            sentence = "  Python is Amazing and FUN!  "

            print(repr(sentence.strip()))
            print(sentence.lower().strip())
            print(sentence.upper().strip())
            print(sentence.strip().replace("Amazing", "Awesome"))
            print(sentence.strip().split())
            print("Count 'a' (ci):", sentence.lower().count("a"))
            print("Starts 'Python':", sentence.strip().startswith("Python"))
        """)
    },
}

# ── Execution helper ───────────────────────────────────────────────────────────
def run_code(code: str, persistent: bool) -> tuple[str, bool, float]:
    """Execute code, return (output, success, elapsed_ms)."""
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    env = st.session_state.persistent_env if persistent else {}
    t0 = time.perf_counter()
    ok = True
    try:
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            exec(compile(code, "<playground>", "exec"), env)  # noqa: S102
    except SystemExit:
        stderr_buf.write("SystemExit called — ignored in sandbox.\n")
        ok = False
    except Exception:
        stderr_buf.write(traceback.format_exc())
        ok = False
    elapsed = (time.perf_counter() - t0) * 1000

    out = stdout_buf.getvalue()
    err = stderr_buf.getvalue()
    combined = ""
    if out:
        combined += out
    if err:
        combined += ("\n" if combined else "") + err
    return combined or "(no output)", ok, elapsed

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-bar">
  <span>🐍</span>
  <h1>Python Learning Environment</h1>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    persistent = st.toggle("Persistent namespace", value=True,
                           help="Keep variables alive between runs")
    show_timer = st.toggle("Show execution time", value=True)

    if st.button("🗑️ Clear namespace"):
        st.session_state.persistent_env = {}
        st.success("Namespace cleared!")

    st.markdown("---")
    st.markdown("## 📚 Code Snippets")
    st.caption("Click a snippet to load it into the editor")

    for title, meta in SNIPPETS.items():
        with st.expander(title):
            st.markdown(f'<div class="snippet-desc">{meta["desc"]}</div>',
                        unsafe_allow_html=True)
            if st.button("Load", key=f"load_{title}"):
                st.session_state.code = meta["code"]
                st.rerun()

    st.markdown("---")
    st.markdown("## 📜 Run History")
    if not st.session_state.history:
        st.caption("No runs yet.")
    else:
        for i, h in enumerate(reversed(st.session_state.history[-8:]), 1):
            badge = "✅" if h["ok"] else "❌"
            with st.expander(f"{badge} Run #{len(st.session_state.history)-i+1}"):
                st.code(h["code"], language="python")
                st.caption(f"⏱ {h['ms']:.1f} ms")

# ── Main layout ────────────────────────────────────────────────────────────────
col_editor, col_output = st.columns([1, 1], gap="large")

with col_editor:
    st.markdown('<div class="editor-label">📝 CODE EDITOR</div>', unsafe_allow_html=True)
    code_input = st.text_area(
        label="editor",
        value=st.session_state.code,
        height=340,
        label_visibility="collapsed",
        key="code_area",
        placeholder="# Write your Python code here…",
    )

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        run_btn = st.button("▶  Run Code", use_container_width=True)
    with c2:
        clear_btn = st.button("🧹 Clear", use_container_width=True)
    with c3:
        copy_hint = st.button("📋 Copy hint", use_container_width=True)

    if clear_btn:
        st.session_state.code = ""
        st.rerun()
    if copy_hint:
        st.info("Use Ctrl+A → Ctrl+C in the editor to copy your code.")

with col_output:
    st.markdown('<div class="editor-label">💻 OUTPUT CONSOLE</div>', unsafe_allow_html=True)

    if run_btn and code_input.strip():
        st.session_state.code = code_input
        with st.spinner("Running…"):
            output, ok, ms = run_code(code_input, persistent)
        st.session_state.history.append({"code": code_input, "output": output, "ok": ok, "ms": ms})

        css_cls = "output-success" if ok else "output-error"
        st.markdown(
            f'<div class="output-box"><span class="{css_cls}">{output}</span></div>',
            unsafe_allow_html=True,
        )

        # status pills
        status_html = f'<span class="stat-pill {"stat-ok" if ok else "stat-err"}">'
        status_html += ("✅ Success" if ok else "❌ Error") + "</span>"
        if show_timer:
            status_html += f'<span class="stat-pill">⏱ {ms:.2f} ms</span>'
        if persistent:
            n_vars = len([k for k in st.session_state.persistent_env
                          if not k.startswith("__")])
            status_html += f'<span class="stat-pill">🔗 {n_vars} var(s) in scope</span>'
        st.markdown(status_html, unsafe_allow_html=True)

    elif run_btn and not code_input.strip():
        st.markdown(
            '<div class="output-box"><span class="output-empty">Nothing to run — write some code first!</span></div>',
            unsafe_allow_html=True,
        )
    else:
        # Show last output if available
        if st.session_state.history:
            last = st.session_state.history[-1]
            css_cls = "output-success" if last["ok"] else "output-error"
            st.markdown(
                f'<div class="output-box"><span class="{css_cls}">{last["output"]}</span></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="output-box"><span class="output-empty">Output will appear here after you run your code…</span></div>',
                unsafe_allow_html=True,
            )

# ── Variable inspector ─────────────────────────────────────────────────────────
if persistent and st.session_state.persistent_env:
    with st.expander("🔍 Variable Inspector", expanded=False):
        vars_display = {
            k: repr(v)
            for k, v in st.session_state.persistent_env.items()
            if not k.startswith("__")
        }
        if vars_display:
            cols = st.columns(3)
            for idx, (k, v) in enumerate(vars_display.items()):
                with cols[idx % 3]:
                    st.markdown(f"**`{k}`**")
                    st.code(v[:120] + ("…" if len(v) > 120 else ""), language="python")
        else:
            st.caption("No user-defined variables yet.")

# ── Quick-reference cheatsheet ─────────────────────────────────────────────────
with st.expander("📖 Python Quick Reference", expanded=False):
    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown("""
**Data types**
```python
int   float   str
bool  list    tuple
dict  set     None
```
**String f-string**
```python
name = "World"
f"Hello, {name}!"
```
""")
    with r2:
        st.markdown("""
**Control flow**
```python
if x > 0:
    ...
elif x == 0:
    ...
else:
    ...

for i in range(5):
    ...

while condition:
    ...
```
""")
    with r3:
        st.markdown("""
**Functions & classes**
```python
def add(a, b=0):
    return a + b

class Cat:
    def __init__(self, n):
        self.name = n
    def meow(self):
        print("Meow!")
```
""")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("🐍 Python Learning Environment - enjoy Learning")
