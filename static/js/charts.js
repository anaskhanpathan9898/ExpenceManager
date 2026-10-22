/**
 * charts.js
 * Fetches data from the Flask API endpoints and renders
 * Chart.js charts on the dashboard page.
 *
 * Dependencies: Chart.js must be loaded before this script.
 */

// Month names for the x-axis labels
const MONTH_NAMES = [
  "Jan","Feb","Mar","Apr","May","Jun",
  "Jul","Aug","Sep","Oct","Nov","Dec"
];

// Colour palette for the doughnut chart slices
const CATEGORY_COLORS = [
  "#4f46e5","#16a34a","#dc2626","#d97706",
  "#0891b2","#7c3aed","#db2777","#64748b"
];

document.addEventListener("DOMContentLoaded", () => {
  renderMonthlyChart();
  renderCategoryChart();
});

/* ==========================================================================
   Monthly bar chart — income vs expenses for each month of the year
   ========================================================================== */
async function renderMonthlyChart() {
  const canvas = document.getElementById("monthlyChart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");

  // Show a loading state
  canvas.style.opacity = "0.4";

  try {
    const year = new Date().getFullYear();
    const res  = await fetch(`/api/monthly-chart?year=${year}`);
    if (!res.ok) throw new Error("Failed to fetch monthly data");

    const data = await res.json();  // [{month:1, income:x, expense:y}, ...]

    const incomeData  = data.map(d => d.income);
    const expenseData = data.map(d => d.expense);

    new Chart(ctx, {
      type: "bar",
      data: {
        labels: MONTH_NAMES,
        datasets: [
          {
            label: "Income",
            data: incomeData,
            backgroundColor: "rgba(22,163,74,.75)",
            borderColor:     "#16a34a",
            borderWidth: 1.5,
            borderRadius: 4,
          },
          {
            label: "Expenses",
            data: expenseData,
            backgroundColor: "rgba(220,38,38,.75)",
            borderColor:     "#dc2626",
            borderWidth: 1.5,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top" },
          tooltip: {
            callbacks: {
              label: ctx => ` ₹${ctx.parsed.y.toFixed(2)}`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: val => `₹${val}`
            }
          }
        }
      }
    });
  } catch (err) {
    console.error("Monthly chart error:", err);
    canvas.parentElement.innerHTML =
      `<p style="color:var(--clr-text-muted);text-align:center;padding:2rem">
         Could not load chart data.
       </p>`;
  } finally {
    canvas.style.opacity = "1";
  }
}

/* ==========================================================================
   Category doughnut chart — spending breakdown by category
   ========================================================================== */
async function renderCategoryChart() {
  const canvas = document.getElementById("categoryChart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  canvas.style.opacity = "0.4";

  try {
    const now   = new Date();
    const year  = now.getFullYear();
    const month = now.getMonth() + 1;   // JS months are 0-indexed
    const res   = await fetch(`/api/category-chart?year=${year}&month=${month}`);
    if (!res.ok) throw new Error("Failed to fetch category data");

    const data = await res.json();  // [{_id:"Food", total:x}, ...]

    if (data.length === 0) {
      canvas.parentElement.innerHTML =
        `<p style="color:var(--clr-text-muted);text-align:center;padding:2rem">
           No expense data for this month.
         </p>`;
      return;
    }

    const labels = data.map(d => d._id);
    const totals = data.map(d => d.total);

    new Chart(ctx, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data: totals,
          backgroundColor: CATEGORY_COLORS.slice(0, labels.length),
          borderWidth: 2,
          borderColor: "#fff",
          hoverOffset: 8,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "right" },
          tooltip: {
            callbacks: {
              label: ctx => ` ₹${ctx.parsed.toFixed(2)}`
            }
          }
        }
      }
    });
  } catch (err) {
    console.error("Category chart error:", err);
    canvas.parentElement.innerHTML =
      `<p style="color:var(--clr-text-muted);text-align:center;padding:2rem">
         Could not load chart data.
       </p>`;
  } finally {
    canvas.style.opacity = "1";
  }
}
