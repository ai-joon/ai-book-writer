import { NextRequest } from 'next/server'
import { cookies } from 'next/headers'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const projectId = searchParams.get('project_id') || '00000000-0000-0000-0000-000000000000'
  const brief = searchParams.get('brief')
  const styleGuide = searchParams.get('style_guide')
  const targetChapters = searchParams.get('target_chapters')
  const model = searchParams.get('model')

  if (!brief) {
    return new Response('Brief is required', { status: 400 })
  }

  // Get cookies from the request
  const cookieStore = cookies()
  const accessToken = cookieStore.get('access_token')
  const refreshToken = cookieStore.get('refresh_token')

  // Forward the request to the backend with cookies
  const backendUrl = process.env.NODE_ENV === 'production'
    ? 'http://sopher-api-service:8000'
    : 'http://localhost:8000'

  const params = new URLSearchParams({
    brief: brief,
    ...(styleGuide && { style_guide: styleGuide }),
    ...(targetChapters && { target_chapters: targetChapters }),
    ...(model && { model: model }),
  })

  const response = await fetch(
    `${backendUrl}/api/v1/projects/${projectId}/outline/stream?${params}`,
    {
      headers: {
        'Cookie': [
          accessToken && `access_token=${accessToken.value}`,
          refreshToken && `refresh_token=${refreshToken.value}`,
        ].filter(Boolean).join('; '),
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
    }
  )

  // Return the stream directly
  return new Response(response.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}