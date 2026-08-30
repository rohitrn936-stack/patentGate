import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { input } = body;

    if (!input || typeof input !== "string" || !input.trim()) {
      return NextResponse.json(
        { success: false, error: "Product description is required" },
        { status: 400 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/agent1`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ input: input.trim() }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { success: false, error: data.error || "Backend request failed" },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Agent 1 API error:", error);
    return NextResponse.json(
      { success: false, error: "Failed to connect to backend" },
      { status: 500 }
    );
  }
}