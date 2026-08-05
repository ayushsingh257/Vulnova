export interface QueryOptimizationRecommendation {
  target_table: string;
  query_pattern: string;
  recommendation: string;
  estimated_impact: string;
}

export interface SlowQueryLog {
  statement: string;
  duration_ms: number;
  timestamp: string;
  table_name?: string;
}

export interface BenchmarkResult {
  query_category: string;
  total_executions: number;
  avg_duration_ms: number;
  p95_duration_ms: number;
  p99_duration_ms: number;
  optimization_status: string;
  recommendation?: string;
}

export interface DatabaseHealthSummary {
  status: "HEALTHY" | "WARNING" | "CRITICAL";
  avg_query_latency_ms: number;
  p95_query_latency_ms: number;
  slow_queries_count_24h: number;
  connection_pool_size: number;
  active_connections: number;
  overflow_connections: number;
  recommendations: QueryOptimizationRecommendation[];
}

export class DatabasePerformanceService {
  private static readonly BASE_URL = "/api/v1/database/performance";

  /**
   * Fetch overall database health, connection pool status, and optimization recommendations.
   */
  public static async getHealth(): Promise<DatabaseHealthSummary> {
    const res = await fetch(`${this.BASE_URL}/health`);
    if (!res.ok) {
      throw new Error("Failed to fetch database health summary.");
    }
    return res.json();
  }

  /**
   * Execute controlled query benchmarking suite.
   */
  public static async runBenchmark(iterations: number = 10): Promise<BenchmarkResult[]> {
    const res = await fetch(`${this.BASE_URL}/benchmark?iterations=${iterations}`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error("Failed to execute database benchmark suite.");
    }
    return res.json();
  }

  /**
   * Fetch captured slow query logs exceeding 100ms.
   */
  public static async getSlowQueries(): Promise<SlowQueryLog[]> {
    const res = await fetch(`${this.BASE_URL}/slow-queries`);
    if (!res.ok) {
      throw new Error("Failed to fetch slow query logs.");
    }
    return res.json();
  }
}
