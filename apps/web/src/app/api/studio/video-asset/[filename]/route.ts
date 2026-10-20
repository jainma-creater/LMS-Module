import { type NextRequest, NextResponse } from "next/server";
import { apiBaseUrl } from "@/lib/config";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ filename: string }> },
) {
  const { filename } = await params;
  const targetUrl = `${apiBaseUrl()}/api/v1/studio/video-asset/${encodeURIComponent(filename)}`;

  try {
    const upstream = await fetch(targetUrl, { cache: "no-store" });
    if (!upstream.ok) {
      return new NextResponse("Video asset not found", { status: upstream.status });
    }

    return new NextResponse(upstream.body, {
      status: 200,
      headers: {
        "content-type": upstream.headers.get("content-type") || "video/mp4",
        "accept-ranges": "bytes",
      },
    });
  } catch {
    return new NextResponse("Failed to proxy video stream", { status: 502 });
  }
}
