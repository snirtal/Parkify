import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { LoginPage } from './LoginPage'

describe('login page', () => {
  it('asks for email and password and has no account-recovery links', () => {
    const html = renderToStaticMarkup(
      <LoginPage notice="The session has expired." onSubmit={() => Promise.resolve()} />,
    )
    expect(html).toContain('type="email"')
    expect(html).toContain('type="password"')
    expect(html).toContain('Show password')
    expect(html).toContain('Sign in')
    expect(html).toContain('The session has expired.')
    expect(html.toLowerCase()).not.toContain('forgot')
    expect(html.toLowerCase()).not.toContain('register')
    expect(html.toLowerCase()).not.toContain('sign up')
    expect(html).not.toContain('localStorage')
    expect(html).not.toContain('<a ')
  })
})
