import { useEffect, useMemo } from 'react'
import { CanvasTexture, SRGBColorSpace } from 'three'
import type { BayStatus } from '../../types/parking'

export interface BayFloorLabel3DProps {
  code: string
  status: BayStatus
  isSelected: boolean
  hasAlert: boolean
  flipUpsideDown?: boolean
}

const BORDER_COLOR: Record<BayStatus, string> = {
  available: '#22d3ee',
  occupied: '#60a5fa',
  reserved: '#c084fc',
  unavailable: '#f59e0b',
}

export function BayFloorLabel3D({
  code,
  status,
  isSelected,
  hasAlert,
  flipUpsideDown = false,
}: BayFloorLabel3DProps) {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 256
    canvas.height = 96
    const ctx = canvas.getContext('2d')

    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const stroke = hasAlert
        ? '#fb7185'
        : isSelected
          ? '#ffffff'
          : BORDER_COLOR[status]

      // Rounded high-contrast surface stencil badge
      const rx = 18
      const x = 10
      const y = 12
      const w = canvas.width - 20
      const h = canvas.height - 24

      ctx.beginPath()
      ctx.roundRect(x, y, w, h, rx)
      ctx.fillStyle = isSelected ? 'rgba(255, 255, 255, 0.96)' : 'rgba(11, 9, 24, 0.86)'
      ctx.fill()

      ctx.lineWidth = isSelected ? 4 : 3
      ctx.strokeStyle = stroke
      ctx.stroke()

      // Bold crisp bay number typography
      ctx.font = '800 42px "SF Pro Display", "Inter", system-ui, sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = isSelected
        ? '#0b0915'
        : status === 'available'
          ? '#67e8f9'
          : '#f8fafc'
      ctx.fillText(code, canvas.width / 2, canvas.height / 2 + 2)
    }

    const tex = new CanvasTexture(canvas)
    tex.colorSpace = SRGBColorSpace
    tex.anisotropy = 8
    tex.needsUpdate = true
    return tex
  }, [code, status, isSelected, hasAlert])

  useEffect(() => {
    return () => {
      texture.dispose()
    }
  }, [texture])

  return (
    <mesh
      rotation={[-Math.PI / 2, 0, flipUpsideDown ? Math.PI : 0]}
      position={[0, 0.028, 1.66]}
    >
      <planeGeometry args={[1.38, 0.52]} />
      <meshBasicMaterial map={texture} transparent depthWrite={false} />
    </mesh>
  )
}
