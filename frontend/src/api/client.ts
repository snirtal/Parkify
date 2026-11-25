export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

export async function apiRequest<T>(
  path: string,
  init: { method?: string; body?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, {
      method: init.method ?? 'GET',
      headers: {
        Accept: 'application/json',
        ...(init.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      signal: init.signal,
    })
  } catch (error) {
    if (isAbortError(error)) throw error
    throw new ApiError(0, 'network_error', 'The server could not be reached.')
  }

  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      throw new ApiError(response.status, 'invalid_response', 'The server returned an unreadable response.')
    }
  }

  if (!response.ok) {
    const record = payload as { error?: { code?: string; message?: string } } | null
    throw new ApiError(
      response.status,
      record?.error?.code ?? 'http_error',
      record?.error?.message ?? 'The request failed.',
    )
  }

  return payload as T
}
