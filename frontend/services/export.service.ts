/**
 * Service handling developer technical remediation exports (JSON, CSV, Markdown).
 */

export type ExportFormat = "json" | "csv" | "markdown";

export class ExportService {
  private static readonly BASE_URL = "/api/v1/reports/export";

  /**
   * Helper to trigger a browser file download from a Blob stream.
   */
  private static downloadBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }

  /**
   * Download bulk organizational findings export in requested format.
   */
  public static async downloadBulkExport(format: ExportFormat): Promise<void> {
    const endpoint = `${this.BASE_URL}/${format}`;
    const res = await fetch(endpoint, {
      method: "GET",
      headers: { Accept: "*/*" },
    });

    if (!res.ok) {
      throw new Error(`Failed to download ${format.toUpperCase()} bulk export (${res.status})`);
    }

    const blob = await res.blob();
    const ext = format === "markdown" ? "md" : format;
    const filename = `Vulnova_Bulk_Technical_Export.${ext}`;
    this.downloadBlob(blob, filename);
  }

  /**
   * Download single vulnerability finding technical package in requested format.
   */
  public static async downloadSingleFindingExport(
    findingId: string,
    format: ExportFormat
  ): Promise<void> {
    const endpoint = `${this.BASE_URL}/${findingId}?format=${format}`;
    const res = await fetch(endpoint, {
      method: "GET",
      headers: { Accept: "*/*" },
    });

    if (!res.ok) {
      throw new Error(`Failed to download single finding ${format.toUpperCase()} export (${res.status})`);
    }

    const blob = await res.blob();
    const ext = format === "markdown" ? "md" : format;
    const filename = `Vulnova_Finding_${findingId.slice(0, 8)}.${ext}`;
    this.downloadBlob(blob, filename);
  }

  /**
   * Fetch text content of a single vulnerability Markdown export for copying to clipboard.
   */
  public static async fetchSingleFindingMarkdown(findingId: string): Promise<string> {
    const endpoint = `${this.BASE_URL}/${findingId}?format=markdown`;
    const res = await fetch(endpoint, {
      method: "GET",
      headers: { Accept: "text/markdown" },
    });

    if (!res.ok) {
      throw new Error(`Failed to fetch Markdown preview (${res.status})`);
    }

    return await res.text();
  }
}
