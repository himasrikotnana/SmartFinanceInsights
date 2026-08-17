// -------------------------
// Monthly Expense Chart
// -------------------------

const expenseCtx = document.getElementById("expenseChart");

const expenseChart = new Chart(expenseCtx, {
    type: "line",
    data: {
        labels: ["Jan","Feb","Mar","Apr","May","Jun"],
        datasets: [{
            label: "Monthly Expense",
            data: [5000,7000,4500,8000,6000,9000],
            borderColor: "#2563eb",
            backgroundColor: "rgba(37,99,235,0.2)",
            fill: true,
            tension: 0.4
        }]
    },
    options: {
        responsive: true
    }
});

// -------------------------
// Expense Category Chart
// -------------------------

const categoryCtx = document.getElementById("categoryChart");

const categoryChart = new Chart(categoryCtx,{
    type:"doughnut",
    data:{
        labels:["Food","Shopping","Travel","Bills"],
        datasets:[{
            data:[30,25,20,25],
            backgroundColor:[
                "#3B82F6",
                "#22C55E",
                "#F59E0B",
                "#EF4444"
            ]
        }]
    },
    options:{
        responsive:true
    }
});

// -------------------------
// Expense Form
// -------------------------

const form = document.getElementById("expenseForm");
const table = document.querySelector("#expenseTable tbody");
const insights = document.getElementById("insights");

let totalExpense = 18500;

form.addEventListener("submit", function(e){

    e.preventDefault();

    const expense = document.getElementById("expense").value;
    const category = document.getElementById("category").value;
    const amount = Number(document.getElementById("amount").value);
    const date = document.getElementById("date").value;

    // Add row

    const row = table.insertRow();

    row.innerHTML = `
        <td>${expense}</td>
        <td>${category}</td>
        <td>₹${amount}</td>
        <td>${date}</td>
    `;

    // Update total expense card

    totalExpense += amount;

    document.querySelector(".expense h2").innerHTML =
        "₹" + totalExpense.toLocaleString();

    // Update savings

    const income = 45000;

    document.querySelector(".savings h2").innerHTML =
        "₹" + (income-totalExpense).toLocaleString();

    // AI Insights

    let message = "";

    if(category=="Food" && amount>1000){

        message="🍔 You spent a high amount on food. Consider reducing dining expenses.";

    }

    else if(category=="Shopping"){

        message="🛍 Shopping expenses are increasing this month.";

    }

    else if(category=="Travel"){

        message="✈ Travel expenses look reasonable.";

    }

    else if(category=="Bills"){

        message="💡 Your bills are within budget.";

    }

    else{

        message="✅ Great! Your spending looks balanced.";

    }

    insights.innerHTML = "<p>"+message+"</p>";

    form.reset();

});