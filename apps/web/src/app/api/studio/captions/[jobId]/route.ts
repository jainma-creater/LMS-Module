import { type NextRequest, NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/config";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await params;
  const targetUrl = `${apiBaseUrl()}/api/v1/studio/captions/${encodeURIComponent(jobId)}`;

  try {
    const upstream = await fetch(targetUrl, { cache: "no-store" });
    if (!upstream.ok) {
      return new NextResponse("Captions not found", { status: upstream.status });
    }

    const vttText = await upstream.text();
    return new NextResponse(vttText, {
      status: 200,
      headers: {
        "content-type": "text/vtt; charset=utf-8",
      },
    });
  } catch {
    return new NextResponse("Failed to proxy captions", { status: 502 });
  }
}
