"""
Đề tài 11: Tối ưu hóa lịch trực bảo vệ bằng Giải thuật Di truyền
=================================================================
Mô tả:
- Khu công nghiệp: 10 cổng, mỗi cổng cần bảo vệ 24/7
- 20 bảo vệ, mỗi người làm tối đa 8 tiếng/ngày, tối thiểu 4 tiếng/ngày
- Ca trực: sáng (6h-14h), chiều (14h-22h), đêm (22h-6h)
- Mỗi bảo vệ nghỉ ít nhất 2 buổi/tuần (mỗi ngày có 3 ca, nghỉ = không được phân ca)
- Tối ưu hóa sự hài lòng về ca trực
"""

import random
import json
import os
import webbrowser
from copy import deepcopy

# ===================== CÀI ĐẶT THAM SỐ =====================
NUM_GUARDS = 20        # số bảo vệ
NUM_DAYS = 7           # số ngày (1 tuần)
NUM_GATES = 10         # số cổng
POPULATION_SIZE = 100  # kích thước quần thể
NUM_GENERATIONS = 200  # số thế hệ
MUTATION_RATE = 0.1    # tỷ lệ đột biến
CROSSOVER_RATE = 0.8   # tỷ lệ lai ghép
ELITE_SIZE = 10        # số cá thể ưu tú giữ lại

# Ca trực: 0=nghỉ, 1=sáng, 2=chiều, 3=đêm
SHIFT_NAMES = {0: "Nghỉ", 1: "Sáng", 2: "Chiều", 3: "Đêm"}
SHIFT_HOURS = {0: 0, 1: 8, 2: 8, 3: 8}  # giờ làm mỗi ca

# Điểm thưởng ca ưa thích
SHIFT_BONUS = {1: 10, 2: 5, 3: 2, 0: 0}

# Phạt
PENALTY_OVERWORK = -15      # làm quá 8 giờ/ngày
PENALTY_UNDERSTAFFED = -50  # thiếu bảo vệ tại một cổng
PENALTY_NO_REST = -200      # không nghỉ đủ 2 buổi/tuần (phạt nặng)

# Tên các ngày trong tuần
DAY_NAMES = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]

# ===================== SINH DỮ LIỆU =====================
def generate_guard_data():
    """Sinh dữ liệu cho 20 bảo vệ với ca ưa thích ngẫu nhiên"""
    random.seed(42)
    guards = []
    shift_prefs = [1, 2, 3]  # Sáng, Chiều, Đêm
    for i in range(NUM_GUARDS):
        preferred_shift = random.choice(shift_prefs)
        guards.append({
            "id": i,
            "name": f"BV_{i+1:02d}",
            "preferred_shift": preferred_shift,
            "max_hours_per_day": 8,
            "min_rest_shifts": 2   # nghỉ ít nhất 2 buổi/tuần
        })
    return guards

GUARDS = generate_guard_data()

# ===================== BIỂU DIỄN NHIỄM SẮC THỂ =====================
# Mỗi cá thể = ma trận (NUM_GUARDS x NUM_DAYS)
# Giá trị mỗi ô: 0=nghỉ, 1=sáng, 2=chiều, 3=đêm

def create_individual():
    """Tạo một cá thể ngẫu nhiên, đảm bảo mỗi bảo vệ có ít nhất 2 buổi nghỉ"""
    individual = []
    for g in range(NUM_GUARDS):
        # Tạo 7 ô ca, mặc định ngẫu nhiên từ 1-3
        schedule = [random.randint(1, 3) for _ in range(NUM_DAYS)]
        # Đảm bảo ít nhất 2 buổi nghỉ (chọn ngẫu nhiên 2 vị trí đặt thành 0)
        rest_positions = random.sample(range(NUM_DAYS), 2)
        for pos in rest_positions:
            schedule[pos] = 0
        individual.append(schedule)
    return individual

def create_population():
    """Tạo quần thể ban đầu"""
    return [create_individual() for _ in range(POPULATION_SIZE)]

# ===================== HÀM FITNESS =====================
def count_guards_per_shift(individual, day):
    """Đếm số bảo vệ theo ca cho một ngày"""
    counts = {1: 0, 2: 0, 3: 0}
    for g in range(NUM_GUARDS):
        shift = individual[g][day]
        if shift in counts:
            counts[shift] += 1
    return counts

def fitness(individual):
    """Tính hàm fitness cho một cá thể"""
    score = 0

    for g in range(NUM_GUARDS):
        guard = GUARDS[g]
        rest_count = 0      # đếm số buổi nghỉ trong tuần

        for d in range(NUM_DAYS):
            shift = individual[g][d]
            hours = SHIFT_HOURS[shift]

            # Thưởng ca ưa thích
            if shift == guard["preferred_shift"]:
                score += SHIFT_BONUS[shift]

            # Kiểm tra làm quá 8 giờ/ngày
            if hours > 8:
                score += PENALTY_OVERWORK

            if shift == 0:
                rest_count += 1   # đây là 1 buổi nghỉ

        # Kiểm tra nghỉ đủ 2 buổi/tuần
        if rest_count < guard["min_rest_shifts"]:
            score += PENALTY_NO_REST * (guard["min_rest_shifts"] - rest_count)

    # Kiểm tra đủ bảo vệ tại mỗi cổng (mỗi ca cần ít nhất ceil(NUM_GATES/NUM_GUARDS_PER_SHIFT) bảo vệ)
    # Mỗi ca cần đủ bảo vệ cho 10 cổng
    min_guards_per_shift = NUM_GATES  # tối thiểu 10 bảo vệ mỗi ca cho 10 cổng

    for d in range(NUM_DAYS):
        counts = count_guards_per_shift(individual, d)
        for shift_id in [1, 2, 3]:
            if counts[shift_id] < min_guards_per_shift:
                # Phạt tùy theo mức thiếu
                shortage = min_guards_per_shift - counts[shift_id]
                score += PENALTY_UNDERSTAFFED * shortage

    return score

# ===================== TOÁN TỬ LẠI GHÉP =====================
def crossover_by_guard(parent1, parent2):
    """Lai ghép theo từng bảo vệ (hoán đổi lịch của một bảo vệ giữa hai cá thể)"""
    if random.random() > CROSSOVER_RATE:
        return deepcopy(parent1), deepcopy(parent2)

    child1 = deepcopy(parent1)
    child2 = deepcopy(parent2)

    # Chọn ngẫu nhiên một số bảo vệ để hoán đổi
    num_swap = random.randint(1, NUM_GUARDS // 2)
    swap_guards = random.sample(range(NUM_GUARDS), num_swap)

    for g in swap_guards:
        child1[g], child2[g] = child2[g][:], child1[g][:]

    return child1, child2

def crossover_by_day(parent1, parent2):
    """Lai ghép theo từng ngày"""
    if random.random() > CROSSOVER_RATE:
        return deepcopy(parent1), deepcopy(parent2)

    child1 = deepcopy(parent1)
    child2 = deepcopy(parent2)

    # Chọn điểm cắt ngẫu nhiên theo ngày
    cut_day = random.randint(1, NUM_DAYS - 1)

    for g in range(NUM_GUARDS):
        child1[g][:cut_day] = parent1[g][:cut_day]
        child1[g][cut_day:] = parent2[g][cut_day:]
        child2[g][:cut_day] = parent2[g][:cut_day]
        child2[g][cut_day:] = parent1[g][cut_day:]

    return child1, child2

# ===================== TOÁN TỬ ĐỘT BIẾN =====================
def mutate(individual):
    """Đột biến: thay đổi ca trực của một bảo vệ vào một ngày nào đó"""
    individual = deepcopy(individual)
    for g in range(NUM_GUARDS):
        for d in range(NUM_DAYS):
            if random.random() < MUTATION_RATE:
                # Thay đổi ca trực sang ca khác (hoặc nghỉ)
                current_shift = individual[g][d]
                new_shift = random.choice([s for s in range(4) if s != current_shift])
                individual[g][d] = new_shift
    return individual

# ===================== CHỌN LỌC =====================
def selection_tournament(population, fitnesses, k=3):
    """Chọn lọc tournament"""
    selected = []
    for _ in range(len(population)):
        contestants = random.sample(range(len(population)), k)
        winner = max(contestants, key=lambda i: fitnesses[i])
        selected.append(deepcopy(population[winner]))
    return selected

# ===================== THUẬT TOÁN DI TRUYỀN CHÍNH =====================
def genetic_algorithm():
    print("=" * 60)
    print("  TỐI ƯU HÓA LỊCH TRỰC BẢO VỆ - GIẢI THUẬT DI TRUYỀN")
    print("=" * 60)
    print(f"  Số bảo vệ: {NUM_GUARDS} | Số cổng: {NUM_GATES} | Số ngày: {NUM_DAYS}")
    print(f"  Quần thể: {POPULATION_SIZE} | Thế hệ: {NUM_GENERATIONS}")
    print("=" * 60)

    # Khởi tạo quần thể
    population = create_population()
    best_fitness_history = []
    avg_fitness_history = []

    best_individual = None
    best_fitness_val = float('-inf')

    for gen in range(NUM_GENERATIONS):
        # Tính fitness cho toàn bộ quần thể
        fitnesses = [fitness(ind) for ind in population]

        # Lưu lại cá thể tốt nhất
        gen_best_idx = max(range(len(population)), key=lambda i: fitnesses[i])
        gen_best_fitness = fitnesses[gen_best_idx]

        if gen_best_fitness > best_fitness_val:
            best_fitness_val = gen_best_fitness
            best_individual = deepcopy(population[gen_best_idx])

        avg_f = sum(fitnesses) / len(fitnesses)
        best_fitness_history.append(best_fitness_val)
        avg_fitness_history.append(avg_f)

        if (gen + 1) % 20 == 0 or gen == 0:
            print(f"  Thế hệ {gen+1:3d} | Best: {best_fitness_val:8.1f} | Avg: {avg_f:8.1f}")

        # Giữ lại cá thể ưu tú (elitism)
        elite_indices = sorted(range(len(population)), key=lambda i: fitnesses[i], reverse=True)[:ELITE_SIZE]
        elites = [deepcopy(population[i]) for i in elite_indices]

        # Chọn lọc
        selected = selection_tournament(population, fitnesses)

        # Lai ghép
        new_population = []
        for i in range(0, len(selected) - 1, 2):
            # Chọn ngẫu nhiên loại lai ghép
            if random.random() < 0.5:
                c1, c2 = crossover_by_guard(selected[i], selected[i+1])
            else:
                c1, c2 = crossover_by_day(selected[i], selected[i+1])
            new_population.extend([c1, c2])

        # Đột biến
        new_population = [mutate(ind) for ind in new_population]

        # Ghép elite vào quần thể mới
        new_population[:ELITE_SIZE] = elites
        population = new_population[:POPULATION_SIZE]

    print("=" * 60)
    print(f"  Kết quả tốt nhất: Fitness = {best_fitness_val:.1f}")
    print("=" * 60)

    return best_individual, best_fitness_history, avg_fitness_history

# ===================== HIỂN THỊ KẾT QUẢ =====================
def print_schedule(individual):
    """In bảng phân lịch trực"""
    print("\n📋 BẢNG PHÂN LỊCH TRỰC (TUẦN)")
    print("-" * 80)
    header = f"{'Bảo vệ':<10}" + "".join(f"{d:<10}" for d in DAY_NAMES)
    print(header)
    print("-" * 80)
    for g in range(NUM_GUARDS):
        guard = GUARDS[g]
        pref = SHIFT_NAMES[guard["preferred_shift"]]
        row = f"{guard['name']:<10}"
        for d in range(NUM_DAYS):
            shift = individual[g][d]
            row += f"{SHIFT_NAMES[shift]:<10}"
        print(f"{row}  (Thích: {pref})")
    print("-" * 80)

def analyze_schedule(individual):
    """Phân tích lịch trực"""
    print("\n📊 PHÂN TÍCH LỊCH TRỰC:")
    print("-" * 50)
    for d in range(NUM_DAYS):
        counts = count_guards_per_shift(individual, d)
        rest = NUM_GUARDS - sum(counts.values())
        print(f"  {DAY_NAMES[d]}: Sáng={counts[1]:2d}, Chiều={counts[2]:2d}, "
              f"Đêm={counts[3]:2d}, Nghỉ(buổi)={rest:2d}")
    print("-" * 50)
    
    # Thống kê số buổi nghỉ mỗi bảo vệ
    print("\n  Số buổi nghỉ mỗi bảo vệ trong tuần:")
    for g in range(NUM_GUARDS):
        rest_shifts = sum(1 for d in range(NUM_DAYS) if individual[g][d] == 0)
        ok = "✅" if rest_shifts >= 2 else "❌"
        print(f"    {GUARDS[g]['name']}: {rest_shifts} buổi nghỉ {ok}")

    total_satisfaction = 0
    for g in range(NUM_GUARDS):
        guard = GUARDS[g]
        satisfied_days = sum(1 for d in range(NUM_DAYS) 
                           if individual[g][d] == guard["preferred_shift"])
        total_satisfaction += satisfied_days
    avg_sat = total_satisfaction / NUM_GUARDS
    print(f"  Số ngày trung bình được ca ưa thích: {avg_sat:.2f}/{NUM_DAYS}")

# ===================== XUẤT HTML =====================
def export_html(individual, best_history, avg_history):
    """Xuất bảng lịch trực và đồ thị hội tụ ra file HTML, tự mở trình duyệt"""

    SHIFT_COLORS = {
        0: ('#dfe6e9', '#636e72'),   # Nghỉ: nền xám, chữ tối
        1: ('#fdcb6e', '#2d3436'),   # Sáng: vàng, chữ tối
        2: ('#e17055', '#ffffff'),   # Chiều: cam, chữ trắng
        3: ('#6c5ce7', '#ffffff'),   # Đêm: tím, chữ trắng
    }

    # Tạo hàng header
    day_headers = "".join(f"<th>{d}</th>" for d in DAY_NAMES)

    # Tạo các hàng bảo vệ
    rows_html = ""
    for g in range(NUM_GUARDS):
        guard = GUARDS[g]
        pref = guard["preferred_shift"]
        pref_name = SHIFT_NAMES[pref]
        rest_count = sum(1 for d in range(NUM_DAYS) if individual[g][d] == 0)
        ok = "✅" if rest_count >= 2 else "❌"

        cells = ""
        for d in range(NUM_DAYS):
            shift = individual[g][d]
            bg, fg = SHIFT_COLORS[shift]
            name = SHIFT_NAMES[shift]
            is_pref = shift == pref and shift != 0
            star = " ★" if is_pref else ""
            cells += (f'<td style="background:{bg};color:{fg};font-weight:bold;'
                      f'border-radius:6px;text-align:center;padding:8px 4px;">'
                      f'{name}{star}</td>')

        rows_html += f"""
        <tr>
            <td style="font-weight:bold;padding:6px 10px;white-space:nowrap">
                {guard['name']}<br>
                <span style="font-size:11px;color:#888">Thích: {pref_name}</span>
            </td>
            {cells}
            <td style="text-align:center;font-size:13px">{ok} {rest_count} buổi</td>
        </tr>"""

    # Dữ liệu đồ thị cho Chart.js
    labels = list(range(1, len(best_history) + 1))
    chart_data = json.dumps({
        "labels": labels,
        "best": best_history,
        "avg": avg_history
    })

    # Thống kê theo ngày
    day_stats = ""
    for d in range(NUM_DAYS):
        counts = count_guards_per_shift(individual, d)
        rest = NUM_GUARDS - sum(counts.values())
        day_stats += f"""
        <tr>
            <td><b>{DAY_NAMES[d]}</b></td>
            <td style="color:#e6a817;font-weight:bold">{counts[1]}</td>
            <td style="color:#e17055;font-weight:bold">{counts[2]}</td>
            <td style="color:#6c5ce7;font-weight:bold">{counts[3]}</td>
            <td style="color:#636e72">{rest}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Lịch Trực Bảo Vệ – Giải Thuật Di Truyền</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; color: #2d3436; }}
  h1 {{ text-align:center; padding: 24px 0 8px; font-size:22px; color:#2d3436; }}
  .subtitle {{ text-align:center; color:#636e72; margin-bottom:24px; font-size:14px; }}
  .container {{ max-width:1100px; margin:0 auto; padding:0 16px 40px; }}
  .card {{ background:#fff; border-radius:12px; box-shadow:0 2px 12px rgba(0,0,0,0.08);
            padding:20px; margin-bottom:24px; }}
  .card h2 {{ font-size:16px; margin-bottom:14px; color:#2d3436; border-left:4px solid #6c5ce7;
              padding-left:10px; }}
  /* Bảng lịch */
  .schedule-wrap {{ overflow-x:auto; }}
  table {{ border-collapse: separate; border-spacing: 4px; width:100%; }}
  thead th {{ background:#2d3436; color:#fff; padding:9px 6px;
              border-radius:6px; text-align:center; font-size:13px; }}
  thead th:first-child {{ text-align:left; padding-left:10px; }}
  tbody tr:hover td {{ opacity:0.88; }}
  tbody td {{ font-size:13px; }}
  /* Chú giải */
  .legend {{ display:flex; gap:14px; flex-wrap:wrap; margin-top:14px; }}
  .legend-item {{ display:flex; align-items:center; gap:6px; font-size:13px; }}
  .legend-box {{ width:18px; height:18px; border-radius:4px; }}
  /* Thống kê */
  .stats-table th {{ background:#f5f6fa; text-align:center; padding:8px; font-size:13px; }}
  .stats-table td {{ text-align:center; padding:7px; font-size:13px; border-bottom:1px solid #f0f0f0; }}
  /* Chart */
  .chart-wrap {{ position:relative; height:320px; }}
  /* note */
  .note {{ font-size:12px; color:#999; margin-top:6px; }}
</style>
</head>
<body>
<h1>🗓️ Lịch Trực Bảo Vệ – Giải Thuật Di Truyền</h1>
<p class="subtitle">Đề tài 11 · 20 bảo vệ · 10 cổng · 7 ngày · ★ = được ca ưa thích</p>

<div class="container">

  <!-- Bảng lịch -->
  <div class="card">
    <h2>📋 Bảng Phân Lịch Trực (1 Tuần)</h2>
    <div class="schedule-wrap">
      <table>
        <thead>
          <tr>
            <th>Bảo vệ</th>
            {day_headers}
            <th>Nghỉ</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    <div class="legend">
      <div class="legend-item"><div class="legend-box" style="background:#dfe6e9;border:1px solid #ccc"></div> Nghỉ</div>
      <div class="legend-item"><div class="legend-box" style="background:#fdcb6e"></div> Ca Sáng (6h–14h)</div>
      <div class="legend-item"><div class="legend-box" style="background:#e17055"></div> Ca Chiều (14h–22h)</div>
      <div class="legend-item"><div class="legend-box" style="background:#6c5ce7"></div> Ca Đêm (22h–6h)</div>
      <div class="legend-item">★ = được ca ưa thích</div>
    </div>
    <p class="note">✅ = đủ 2 buổi nghỉ &nbsp;|&nbsp; ❌ = chưa đủ</p>
  </div>

  <!-- Thống kê theo ngày -->
  <div class="card">
    <h2>📊 Số Bảo Vệ Theo Ca Mỗi Ngày</h2>
    <table class="stats-table">
      <thead><tr><th>Ngày</th><th>☀️ Sáng</th><th>🌇 Chiều</th><th>🌙 Đêm</th><th>😴 Nghỉ</th></tr></thead>
      <tbody>{day_stats}</tbody>
    </table>
  </div>

  <!-- Đồ thị hội tụ -->
  <div class="card">
    <h2>📈 Đồ Thị Hội Tụ Hàm Fitness Qua Các Thế Hệ</h2>
    <div class="chart-wrap">
      <canvas id="fitnessChart"></canvas>
    </div>
  </div>

</div>

<script>
const data = {chart_data};
const ctx = document.getElementById('fitnessChart').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: data.labels,
    datasets: [
      {{
        label: 'Fitness tốt nhất',
        data: data.best,
        borderColor: '#00b894',
        backgroundColor: 'rgba(0,184,148,0.08)',
        borderWidth: 2.5,
        pointRadius: 0,
        fill: true,
        tension: 0.3
      }},
      {{
        label: 'Fitness trung bình',
        data: data.avg,
        borderColor: '#6c5ce7',
        backgroundColor: 'rgba(108,92,231,0.06)',
        borderWidth: 2,
        borderDash: [6,3],
        pointRadius: 0,
        fill: true,
        tension: 0.3
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'top', labels: {{ font: {{ size: 13 }} }} }},
      tooltip: {{ mode: 'index', intersect: false }}
    }},
    scales: {{
      x: {{ title: {{ display: true, text: 'Thế hệ', font: {{ size: 13 }} }} }},
      y: {{ title: {{ display: true, text: 'Giá trị Fitness', font: {{ size: 13 }} }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

    # Lưu file HTML
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lich_truc.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✅ Đã xuất bảng lịch: {output_path}")
    # Tự động mở trình duyệt
    webbrowser.open(f"file:///{output_path.replace(os.sep, '/')}")
    print("  🌐 Đang mở trình duyệt...")


# ===================== CHẠY CHÍNH =====================
if __name__ == "__main__":
    # In thông tin bảo vệ
    print("\n👥 THÔNG TIN 20 BẢO VỆ:")
    print("-" * 40)
    for g in GUARDS:
        print(f"  {g['name']}: Ca ưa thích = {SHIFT_NAMES[g['preferred_shift']]}")

    # Chạy thuật toán di truyền
    best_ind, best_hist, avg_hist = genetic_algorithm()

    # Hiển thị kết quả
    print_schedule(best_ind)
    analyze_schedule(best_ind)

    # Xuất HTML (bảng màu + đồ thị hội tụ)
    print("\n📈 Đang xuất HTML...")
    export_html(best_ind, best_hist, avg_hist)

    print("\n✅ Hoàn thành! File lich_truc.html đã được mở trong trình duyệt.")
