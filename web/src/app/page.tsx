"use client";

import { useEffect, useState } from "react";
import { format, addMonths, subMonths } from "date-fns";
import { ChevronLeft, ChevronRight, Wallet, TrendingDown } from "lucide-react";

interface CategoryData {
  id: number;
  name: string;
  budgeted: number;
  activity: number;
  available: number;
}

interface GroupData {
  id: number;
  name: string;
  categories: CategoryData[];
}

interface BudgetData {
  month: string;
  readyToAssign: number;
  groups: GroupData[];
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
}

export default function BudgetPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [budgetData, setBudgetData] = useState<BudgetData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedGroups, setExpandedGroups] = useState<Set<number>>(new Set());

  const monthKey = format(currentMonth, "yyyy-MM");

  useEffect(() => {
    loadBudget();
  }, [monthKey]);

  const loadBudget = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/budget?month=${monthKey}`);
      const data = await res.json();
      setBudgetData(data);
      // Expand all groups by default
      setExpandedGroups(new Set(data.groups.map((g: GroupData) => g.id)));
    } catch (error) {
      console.error("Failed to load budget:", error);
    }
    setLoading(false);
  };

  const toggleGroup = (groupId: number) => {
    const next = new Set(expandedGroups);
    if (next.has(groupId)) {
      next.delete(groupId);
    } else {
      next.add(groupId);
    }
    setExpandedGroups(next);
  };

  // Calculate totals
  const totalBudgeted =
    budgetData?.groups?.reduce(
      (sum, g) => sum + g.categories.reduce((s, c) => s + c.budgeted, 0),
      0
    ) || 0;

  const totalActivity =
    budgetData?.groups?.reduce(
      (sum, g) => sum + g.categories.reduce((s, c) => s + c.activity, 0),
      0
    ) || 0;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      {/* Header */}
      <header className="border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">
              Zeroed
            </h1>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
                className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <span className="text-lg font-medium min-w-[140px] text-center">
                {format(currentMonth, "MMMM yyyy")}
              </span>
              <button
                onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
                className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">
        {/* Ready to Assign Banner */}
        <div
          className={`p-6 rounded-xl ${
            (budgetData?.readyToAssign || 0) >= 0
              ? "bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800"
              : "bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800"
          }`}
        >
          <p className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
            Ready to Assign
          </p>
          <p
            className={`text-4xl font-bold ${
              (budgetData?.readyToAssign || 0) >= 0
                ? "text-green-600 dark:text-green-400"
                : "text-red-600 dark:text-red-400"
            }`}
          >
            {formatCurrency(budgetData?.readyToAssign || 0)}
          </p>
          {(budgetData?.readyToAssign || 0) < 0 && (
            <p className="text-sm text-red-600 dark:text-red-400 mt-1">
              You&apos;ve budgeted more than available
            </p>
          )}
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white dark:bg-zinc-900 rounded-xl p-4 border border-zinc-200 dark:border-zinc-800">
            <div className="flex items-center gap-2 text-zinc-500 mb-1">
              <Wallet className="w-4 h-4" />
              <span className="text-sm">Total Budgeted</span>
            </div>
            <p className="text-2xl font-semibold text-zinc-900 dark:text-white">
              {formatCurrency(totalBudgeted)}
            </p>
          </div>
          <div className="bg-white dark:bg-zinc-900 rounded-xl p-4 border border-zinc-200 dark:border-zinc-800">
            <div className="flex items-center gap-2 text-zinc-500 mb-1">
              <TrendingDown className="w-4 h-4" />
              <span className="text-sm">Total Spending</span>
            </div>
            <p className="text-2xl font-semibold text-red-600">
              {formatCurrency(Math.abs(totalActivity))}
            </p>
          </div>
        </div>

        {/* Budget Table */}
        <div className="bg-white dark:bg-zinc-900 rounded-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden">
          <table className="w-full">
            <thead className="bg-zinc-50 dark:bg-zinc-800/50">
              <tr className="text-sm text-zinc-500 dark:text-zinc-400">
                <th className="text-left p-4 font-medium">Category</th>
                <th className="text-right p-4 font-medium">Budgeted</th>
                <th className="text-right p-4 font-medium">Activity</th>
                <th className="text-right p-4 font-medium">Available</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} className="p-8 text-center text-zinc-500">
                    Loading...
                  </td>
                </tr>
              ) : (
                budgetData?.groups.map((group) => (
                  <>
                    {/* Group Header */}
                    <tr
                      key={`group-${group.id}`}
                      className="bg-zinc-50/50 dark:bg-zinc-800/30 cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
                      onClick={() => toggleGroup(group.id)}
                    >
                      <td className="p-4 font-semibold text-zinc-900 dark:text-white">
                        <span className="mr-2">
                          {expandedGroups.has(group.id) ? "▼" : "▶"}
                        </span>
                        {group.name}
                      </td>
                      <td className="text-right p-4 text-zinc-500">
                        {formatCurrency(
                          group.categories.reduce((s, c) => s + c.budgeted, 0)
                        )}
                      </td>
                      <td className="text-right p-4 text-zinc-500">
                        {formatCurrency(
                          group.categories.reduce((s, c) => s + c.activity, 0)
                        )}
                      </td>
                      <td className="text-right p-4 text-zinc-500">
                        {formatCurrency(
                          group.categories.reduce((s, c) => s + c.available, 0)
                        )}
                      </td>
                    </tr>

                    {/* Categories */}
                    {expandedGroups.has(group.id) &&
                      group.categories.map((cat) => (
                        <tr
                          key={`cat-${cat.id}`}
                          className="border-t border-zinc-100 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/20"
                        >
                          <td className="p-4 pl-10 text-zinc-700 dark:text-zinc-300">
                            {cat.name}
                          </td>
                          <td className="text-right p-4 text-zinc-900 dark:text-white">
                            {formatCurrency(cat.budgeted)}
                          </td>
                          <td
                            className={`text-right p-4 ${
                              cat.activity < 0
                                ? "text-red-600"
                                : cat.activity > 0
                                  ? "text-green-600"
                                  : "text-zinc-400"
                            }`}
                          >
                            {formatCurrency(cat.activity)}
                          </td>
                          <td
                            className={`text-right p-4 font-medium ${
                              cat.available < 0
                                ? "text-red-600 bg-red-50 dark:bg-red-950"
                                : cat.available > 0
                                  ? "text-green-600"
                                  : "text-zinc-400"
                            }`}
                          >
                            {formatCurrency(cat.available)}
                          </td>
                        </tr>
                      ))}
                  </>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
