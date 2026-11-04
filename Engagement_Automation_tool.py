import streamlit as st
st.set_page_config(page_title="ESG Extractor", layout="centered")
import os
import re
import fitz  # PyMuPDF
from datetime import datetime
import sys
import math
import pandas as pd
from io import BytesIO


CREDENTIALS = st.secrets["credentials"]


# --- Login logic ---
def login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("🔐 Engagement Automation tool")
        
        # Use a form to prevent Streamlit from rerunning on every keystroke
        with st.form("login_form"):
            username = st.text_input("Username", key="username_input")
            password = st.text_input("Password", type="password", key="password_input")
            submitted = st.form_submit_button("Login")

            if submitted:
                if username in CREDENTIALS and CREDENTIALS[username] == password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
        st.stop()

login() 

color_map = {
    (231, 180, 22): 3, (192, 0, 0): 1, (30, 115, 59): 5,
    (170, 191, 177): 4, (189, 202, 171): 4, (110, 160, 37): 4,
    (219, 207, 168): 3, (225, 132, 49): 2, (219, 136, 54): 2,
    (210, 163, 162): 1,(229, 229, 229):0
}

#LEGEND_RECT = fitz.Rect(835, 205, 890, 390)

#legend_rect= fitz.Rect(808, 253, 855, 403)
legend_rect = fitz.Rect(835, 205, 890, 390)

def log_message(message, log_file):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"{now} - {message}"
    print(formatted_message)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(formatted_message + "\n")

def get_closest_score(r, g, b, color_map, tolerance=20000):
    """
    Returns the score corresponding to the closest color in color_map within a given tolerance.

    Parameters:
        r, g, b (int): RGB values of the color to match.
        color_map (dict): Dictionary mapping (R, G, B) tuples to scores.
        tolerance (int): Maximum squared distance allowed for a match.

    Returns:
        int or None: The closest score if within tolerance, otherwise None.
    """
    min_dist, closest_score = float('inf'), None   #float(inf) = positive infinity
    #log_message(f"Checking closest score for color ({r}, {g}, {b})", log_file)
    for (cr, cg, cb), score in color_map.items():
        dist = math.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2)
        #log_message(f"→ Compared with ({cr}, {cg}, {cb}), score={score}, dist={dist}", log_file)
        if dist < min_dist and dist < tolerance:
            min_dist = dist
            closest_score = score
            #log_message(f"→ New closest color: ({cr}, {cg}, {cb}) with score {score} and distance {dist}", log_file)
    if closest_score is None:
        print("")
        #log_message(f"No close match found for color ({r}, {g}, {b}) within tolerance {tolerance}", log_file)
       # messagebox.showerror(f"No close match found",f"No close match found for color ({r}, {g}, {b}) within tolerance {tolerance}")
        print(f"No close match found",f"No close match found for color ({r}, {g}, {b}) within tolerance {tolerance}")
    else:
        print("")
        #log_message(f"Closest match for ({r}, {g}, {b}) is score {closest_score}", log_file)
    return closest_score


import fitz  # PyMuPDF

def draw_debug_box(page, x, y, size=10, color=(1, 0, 0), fill_opacity=0.2):
    """
    Draws a semi-transparent box around the sampled area for visual debugging.
    
    Args:
        page (fitz.Page): The page to draw on.
        x (int): Center x-coordinate.
        y (int): Center y-coordinate.
        size (int): Half-length of the box.
        color (tuple): RGB in 0–1 format (e.g., red = (1, 0, 0)).
        fill_opacity (float): Fill opacity (0 = transparent, 1 = solid).
    """
    rect = fitz.Rect(x - size, y - size, x + size, y + size)
    shape = page.new_shape()
    shape.draw_rect(rect)
    shape.finish(color=color, fill=color, fill_opacity=fill_opacity)
    shape.commit()



def average_color(pix, cx, cy, sample_size=3):
    
    """
    Computes the average RGB color around a central point (cx, cy) in a square of size sample_size.
    """
    
    colors = []
    offset = sample_size // 2
    #log_message(f"Sampling average color around pixel ({cx}, {cy}) with sample size {sample_size}", log_file)
    
    for dx in range(-offset, offset + 1):
        for dy in range(-offset, offset + 1):
            x, y = cx + dx, cy + dy
            if 0 <= x < pix.width and 0 <= y < pix.height:
                rgb_sample = pix.pixel(x, y)[:3]
                colors.append(rgb_sample)
                #log_message(f"→ Sampled pixel ({x}, {y}) = {rgb_sample}", log_file)
            else:
                #log_message(f"→ Skipped out-of-bound pixel ({x}, {y})", log_file)
                print("")
    if not colors:
       #log_message(f"No valid pixels sampled around ({cx}, {cy}), returning white", log_file)
       #messagebox.showerror("returning white",f"No valid pixels sampled around ({cx}, {cy}), returning white")
       print("returning white",f"No valid pixels sampled around ({cx}, {cy}), returning white")
       return (255, 255, 255)
    avg_rgb = tuple(sum(c[i] for c in colors) // len(colors) for i in range(3))
    #return tuple(sum(c[i] for c in colors) // len(colors) for i in range(3))
    
    #log_message(f"Average color at ({cx}, {cy}) is {avg_rgb} based on {len(colors)} pixels", log_file)

    return avg_rgb
    

def sample_average_color(page, rect, scale=3, sample_size=3):
    pix = page.get_pixmap(clip=rect, matrix=fitz.Matrix(scale, scale))
    cx, cy = pix.width // 2, pix.height // 2
    return average_color(pix, cx, cy, sample_size)




def detect_intermediate_scores(page, table, color_map):
    results = []
    for i, row in enumerate(table.rows[1:]):
        print(i)
        try:
            inum = 2
            for j in range(len(row.cells)-1, 1, -1):
                print(j)
                print(row.cells,len(row.cells))
                if row.cells[j] is not None:
                    inum = j
                    break

            #row.cells[0]
            cell = row.cells[inum] if len(row.cells) >2 else None
            if not (isinstance(cell, (tuple, list)) and len(cell) == 4):
                results.append(None)
                continue

            rect = fitz.Rect(cell)
            color = sample_average_color(page, rect)

            if max(color) - min(color) < 15 or sum(color) / 3 > 240:
                results.append(0)
                continue

            score = get_closest_score(*color, color_map)

        except Exception:
            score = None

        results.append(score)
    return results


def detect_total_score_by_position(page, legend_rect):
    """
    Detects total score by identifying the most saturated/unique color 
    and mapping it based on its vertical position.
    Score 5 is at top, score 1 is at bottom.
    """
    try:
        pix = page.get_pixmap(clip=legend_rect, matrix=fitz.Matrix(3, 3), alpha=True)
        step = pix.height // 5
        #centers = [(pix.width // 2, step // 2 + step * i) for i in range(5)]
        #offset_y = int(step * 0.6)  # adjust this based on spacing 
        #centers = [(pix.width // 2, offset_y + step * i) for i in range(5)] #not working on red
        centers = [
                (pix.width // 2, int(step * 0.6) + step * 0),  # top (score 5)
                (pix.width // 2, int(step * 0.6) + step * 1),
                (pix.width // 2, int(step * 0.6) + step * 2),
                (pix.width // 2, int(step * 0.6) + step * 3),
                (pix.width // 2, int(step * 0.45) + step * 4), # bottom (score 1) — slightly lifted
                ]

        best_saturation = -1
        best_index = -1

        for idx, (x, y) in enumerate(centers):
            offset = 2
            r_sum = g_sum = b_sum = a_sum = 0
            count = 0

            for dx in range(-offset, offset + 1):
                for dy in range(-offset, offset + 1):
                    px = (y + dy) * pix.width + (x + dx)
                    r, g, b, a = pix.samples[4 * px: 4 * px + 4]
                    r_sum += r; g_sum += g; b_sum += b
                    count += 1

            avg_r = r_sum // count
            avg_g = g_sum // count
            avg_b = b_sum // count

            # Use saturation to detect "most vivid" circle (likely opaque)
            r_norm, g_norm, b_norm = [v / 255 for v in (avg_r, avg_g, avg_b)]
            max_c = max(r_norm, g_norm, b_norm)
            min_c = min(r_norm, g_norm, b_norm)
            saturation = (max_c - min_c) / max_c if max_c > 0 else 0

            print(f"Sample {idx}: RGB=({avg_r}, {avg_g}, {avg_b}), Saturation={saturation:.2f}")

            if saturation > best_saturation:
                best_saturation = saturation
                best_index = idx

        if best_index != -1:
            score = 5 - best_index  # Top = 5, bottom = 1
            print(f"Detected Total Score: {score}")
            return score
        else:
            print("No vivid circle found")
            return None

    except Exception as e:
        print(f"Total score detection error: {e}")
        return None


def extract_page_data(page, filename, legend_rect, color_map):
    text = page.get_text()
    if not all(x in text for x in ["KPI", "Comment", "KPI Score"]):
        if not all(x in text for x in ["KPI", "Comment", "Intermediate"]):
            return []

    company_match = re.match(r'RSG Full Engagement (.+?) \d{4}', filename)
    company = company_match.group(1).strip() if company_match else "Unknown"
    year = re.search(r'(\d{4})', filename).group(1) if re.search(r'(\d{4})', filename) else "0000"
    topic = "Unknown Topic"
    for line in text.split('\n'):
        if re.search(r'\s+\d+/\d+$', line.strip()):
            topic = re.sub(r'\s+\d+/\d+$', '', line.strip())
            break

    tables = page.find_tables()
    
    total_score = detect_total_score_by_position(page, legend_rect)
    
    page_data=[]
    
    if not tables:
        log_message(f"{filename} Page {page.number + 1}: No tables found", "error_log.txt")
       # log_message(f"{filename} Page {page.number + 1}: No tables found", "error_log.txt")
        #messagebox.showerror("No tables found",f"{filename} Page {page.number + 1}: No tables found")
        print("No tables found",f"{filename} Page {page.number + 1}: No tables found")
        
        return []

    if tables:
        intermediate_scores = detect_intermediate_scores(page, tables[1], color_map)

        for idx, row in enumerate(tables[1].rows[1:6]):
            print(idx, row)
            try:
                if len(row.cells) < 3:
                    continue

                kpi = ""
                comment = ""
                score = intermediate_scores[idx] if idx < len(intermediate_scores) else ""

                num = 0
# =============================================================================
#                 for i in range(0, 3):
#                     if row.cells[i] is None:
#                         num = i + 1
#                         continue
# =============================================================================

                if isinstance(row.cells[num], (tuple, list)) and len(row.cells[num]) == 4:
                    kpi_rect = fitz.Rect(row.cells[num])
                    kpi = " ".join(page.get_text("text", clip=kpi_rect).strip().replace('\n', ' ').split())

                if isinstance(row.cells[num + 1], (tuple, list)) and len(row.cells[num + 1]) == 4:
                    comment_rect = fitz.Rect(row.cells[num + 1])
                    comment = page.get_text("text", clip=comment_rect)

                comment = re.sub(r'[•●]', '_', comment)
                lines = comment.strip().splitlines()
                bullets = []
                for line in lines:
                    line = line.strip()
                    if line.startswith('_'):
                        clean_line = line.lstrip('_').strip()
                        bullets.append(clean_line)
                    elif bullets:
                        bullets[-1] += ' ' + line
                comment_clean = ''.join(f"-{b}\n" for b in bullets)
                comment=comment_clean
                #comment = comment_clean.replace('\n', '\\n')

                page_data.append({
                    "Company": company,
                    "Year": int(year),
                    "Topic": topic,
                   "Total_Score": total_score if total_score is not None else "",
                    "KPI": kpi,
                    "Comment": comment,
                   "Score": score if score is not None else "",
                    "Page": page.number + 1
                })
            except Exception:
                continue

        if len(page_data) > 1:
            return page_data


def check_data_quality(data_list):
    issues = []
    if any(not d.get("KPI") for d in data_list): issues.append("Missing KPI")
    if any(not d.get("Comment") for d in data_list): issues.append("Missing Comment")
    if any(d.get("Score") == "" for d in data_list): issues.append("Missing Score")
    if any(d.get("Total_Score") == "" for d in data_list): issues.append("Missing Total Score")
    return ("PARTIAL", ", ".join(issues)) if issues else ("SUCCESS", "")

def process_pdf_file(pdf_path, output_folder, legend_rect, color_map, log_file):
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    try:
        doc = fitz.open(pdf_path)

        all_data = []
        for page in doc:
            print(page)
            page_data = extract_page_data(page, os.path.basename(pdf_path), legend_rect, color_map)
            if page_data:
                all_data.extend(page_data)
                         
        if all_data:
            df = pd.DataFrame(all_data)
            status, details = check_data_quality(all_data)
            log_message(f"{base_name}: {status}" + (f" - {details}" if details else ""), log_file)
            return df
        else:
            log_message(f"{base_name}: FAILURE - No extractable data found", log_file)
            #messagebox.showerror("No extractable data found",f"{base_name}: FAILURE - No extractable data found")
            print("No extractable data found",f"{base_name}: FAILURE - No extractable data found")
            return False
    except Exception as e:
        log_message(f"{base_name}: FAILURE - {e}", log_file)
        #messagebox.showerror(f"{base_name}: FAILURE - {e}",f"{base_name}: FAILURE - {e}")
        print(f"{base_name}: FAILURE - {e}",f"{base_name}: FAILURE - {e}")
        return False


def process_pdf_folder(input_folder, output_folder, legend_rect, color_map, log_file):
    final_df=pd.DataFrame()
    os.makedirs(output_folder, exist_ok=True)
    log_message("Starting PDF processing...", log_file)
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
    if not pdf_files:
        #messagebox.showinfo("Error: No PDF documents found.")
        st.error("No PDF documents found.", "Error: No PDF documents found.")
        print("No PDF documents found.", "Error: No PDF documents found.")
        log_message("Error: No PDF documents found.", log_file)
        sys.exit()
    for pdf_file in pdf_files:
        log_message(f"Processing {pdf_file}...", log_file)
        success = process_pdf_file(os.path.join(input_folder, pdf_file), output_folder, legend_rect, color_map, log_file)
        if len(success)<1:
            log_message(f"Error: {pdf_file} processing failed.", log_file)
            #messagebox.showerror(f"Error: {pdf_file} processing failed.",f"Error: {pdf_file} processing failed.")
            print(f"Error: {pdf_file} processing failed.",f"Error: {pdf_file} processing failed.")
        else:
            final_df = pd.concat([final_df,success])
    return final_df       


st.title("📄 PDF Data Extractor")

uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)

if uploaded_files:
    st.info("🔄 Processing PDFs...")

    all_data = []
    logs = []
    now = datetime.now().strftime("%Y%m%d_%H%M")

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        try:
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            file_data = []

            for page in doc:
                page_data = extract_page_data(page, filename, legend_rect, color_map)
                if page_data:
                    file_data.extend(page_data)

            if file_data:
                all_data.extend(file_data)
                status, details = check_data_quality(file_data)
                logs.append(f"{filename}: {status}" + (f" - {details}" if details else ""))
            else:
                logs.append(f"{filename}: FAILURE - No data extracted")

            doc.close()
        except Exception as e:
            logs.append(f"{filename}: FAILURE - {str(e)}")

    st.subheader("🔍 Extraction Log")
    for log in logs:
        st.write(log)

    if all_data:
        df = pd.DataFrame(all_data)
        st.subheader("📊 Extracted Data")
        st.dataframe(df)

        output = BytesIO()
        df.to_excel(output, index=False, engine='xlsxwriter')
        output.seek(0)

        st.download_button(
            label="📥 Download Combined Excel",
            data=output,
            file_name=f"ESG_Extracted_{now}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("❌ No data extracted from any PDFs.")
else:
    st.warning("⚠️ Please upload one or more PDF files to begin.")
