import { Billboard, RoundedBox } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useMemo, useRef, useState } from 'react'
import { Shape, type Group, type Mesh } from 'three'
import type { BayStatus, ParkingBay } from '../../types/parking'
import { BayFloorLabel3D } from './BayFloorLabel3D'
import { StylizedCar3D } from './StylizedCar3D'

export interface ParkingBay3DProps {
  bay: ParkingBay
  position: [number, number, number]
  rotationY: number
  isSelected: boolean
  isDimmed: boolean
  onSelect: (bayId: string) => void
}

const STATUS_COLORS: Record<BayStatus, { pad: string; glow: string }> = {
  available: { pad: '#22d3ee', glow: '#06b6d4' },
  occupied: { pad: '#3b82f6', glow: '#60a5fa' },
  reserved: { pad: '#a855f7', glow: '#c084fc' },
  unavailable: { pad: '#f59e0b', glow: '#fbbf24' },
}

export function ParkingBay3D({
  bay,
  position,
  rotationY,
  isSelected,
  isDimmed,
  onSelect,
}: ParkingBay3DProps) {
  const [hovered, setHovered] = useState(false)
  const beaconRef = useRef<Group>(null)
  const alertBillboardRef = useRef<Group>(null)
  const pulseRingRef = useRef<Mesh>(null)

  const hasAlert = Boolean(bay.vehicle?.hasAlert)
  const palette = hasAlert
    ? { pad: '#f43f5e', glow: '#fb7185' }
    : STATUS_COLORS[bay.status]

  const triangleShape = useMemo(() => {
    const s = new Shape()
    s.moveTo(0, 0.22)
    s.lineTo(-0.21, -0.15)
    s.lineTo(0.21, -0.15)
    s.closePath()
    return s
  }, [])

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime()
    if (beaconRef.current) {
      beaconRef.current.rotation.y = t * 1.1
      beaconRef.current.position.y = 0.62 + Math.sin(t * 2.2) * 0.07
    }
    if (alertBillboardRef.current) {
      alertBillboardRef.current.position.y = 2.08 + Math.sin(t * 2.8) * 0.08
    }
    if (pulseRingRef.current) {
      const pulse = 0.22 + Math.sin(t * 3.4) * 0.08
      const mat = pulseRingRef.current.material
      if ('opacity' in mat) {
        mat.opacity = isDimmed
          ? 0.04
          : isSelected
            ? pulse + 0.2
            : hasAlert
              ? pulse + 0.16
              : bay.status === 'available'
                ? 0.22
                : bay.status === 'reserved'
                  ? 0.24
                  : 0.14
      }
    }
  })

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      {/* Interactive invisible hit box covering stall + car */}
      <mesh
        position={[0, 0.7, 0]}
        onClick={(e) => {
          e.stopPropagation()
          onSelect(bay.id)
        }}
        onPointerOver={(e) => {
          e.stopPropagation()
          setHovered(true)
          document.body.style.cursor = 'pointer'
        }}
        onPointerOut={() => {
          setHovered(false)
          document.body.style.cursor = 'auto'
        }}
      >
        <boxGeometry args={[2.55, 1.8, 4.7]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* Glowing status floor pad */}
      <mesh
        ref={pulseRingRef}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0.015, -0.05]}
        receiveShadow
      >
        <planeGeometry args={[2.32, 4.18]} />
        <meshBasicMaterial
          color={palette.pad}
          transparent
          opacity={0.18}
        />
      </mesh>

      {/* Crisp painted side parking lines */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[-1.22, 0.02, 0]}>
        <planeGeometry args={[0.085, 4.25]} />
        <meshBasicMaterial
          color={isSelected ? '#ffffff' : '#e2dff8'}
          transparent
          opacity={isDimmed ? 0.22 : isSelected ? 1 : 0.78}
        />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[1.22, 0.02, 0]}>
        <planeGeometry args={[0.085, 4.25]} />
        <meshBasicMaterial
          color={isSelected ? '#ffffff' : '#e2dff8'}
          transparent
          opacity={isDimmed ? 0.22 : isSelected ? 1 : 0.78}
        />
      </mesh>

      {/* Glowing front threshold indicator bar */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.024, 2.12]}>
        <planeGeometry args={[1.8, 0.1]} />
        <meshBasicMaterial
          color={palette.glow}
          transparent
          opacity={isDimmed ? 0.2 : isSelected || hovered ? 1 : 0.8}
        />
      </mesh>

      {/* Clear 3D Surface Parking Space Number Stencil (oriented right-side-up to viewer!) */}
      <BayFloorLabel3D
        code={bay.code}
        status={bay.status}
        isSelected={isSelected}
        hasAlert={hasAlert}
        flipUpsideDown={Math.abs(rotationY) > 0.1}
      />

      {/* Selection perimeter highlight */}
      {(isSelected || hovered) && (
        <mesh position={[0, 0.03, -0.05]}>
          <boxGeometry args={[2.38, 0.03, 4.24]} />
          <meshStandardMaterial
            color={palette.glow}
            emissive={palette.glow}
            emissiveIntensity={isSelected ? 1.9 : 1.0}
            transparent
            opacity={isSelected ? 0.36 : 0.2}
          />
        </mesh>
      )}

      {/* Ambient point light for alerted or selected bay */}
      {(hasAlert || isSelected) && !isDimmed && (
        <pointLight
          position={[0, 1.6, 0.2]}
          color={hasAlert ? '#f43f5e' : palette.glow}
          intensity={hasAlert ? 4.8 : 3.2}
          distance={6.2}
        />
      )}

      {/* OCCUPIED: Sculpted 3D Vehicle */}
      {bay.status === 'occupied' && bay.vehicle && (
        <group position={[0, 0, -0.18]} scale={isDimmed ? 0.98 : 1}>
          <StylizedCar3D
            colorHex={bay.vehicle.colorHex}
            accentHex={hasAlert ? '#f43f5e' : bay.vehicle.accentHex}
            bodyType={bay.vehicle.bodyType}
            isHighlighted={isSelected || hovered || hasAlert}
          />
        </group>
      )}

      {/* RESERVED: Floating Neon Purple Holo-Diamond */}
      {bay.status === 'reserved' && (
        <group ref={beaconRef} position={[0, 0.62, -0.15]}>
          <mesh>
            <octahedronGeometry args={[0.28, 0]} />
            <meshStandardMaterial
              color="#d8b4fe"
              emissive="#a855f7"
              emissiveIntensity={2.4}
              roughness={0.15}
              metalness={0.6}
            />
          </mesh>
        </group>
      )}

      {/* UNAVAILABLE: Sleek Maintenance Barrier Bar */}
      {bay.status === 'unavailable' && (
        <group position={[0, 0.3, 0.45]}>
          <RoundedBox args={[1.72, 0.15, 0.15]} radius={0.04} smoothness={2}>
            <meshStandardMaterial
              color="#1e293b"
              emissive="#f59e0b"
              emissiveIntensity={1.15}
            />
          </RoundedBox>
          <mesh position={[-0.72, -0.15, 0]}>
            <cylinderGeometry args={[0.06, 0.08, 0.3, 12]} />
            <meshStandardMaterial color="#475569" />
          </mesh>
          <mesh position={[0.72, -0.15, 0]}>
            <cylinderGeometry args={[0.06, 0.08, 0.3, 12]} />
            <meshStandardMaterial color="#475569" />
          </mesh>
        </group>
      )}

      {/* True 3D Billboard Circular Warning Beacon above Alerted Car */}
      {hasAlert && !isDimmed && (
        <group ref={alertBillboardRef} position={[0, 2.08, -0.25]}>
          <Billboard
            onClick={(e) => {
              e.stopPropagation()
              onSelect(bay.id)
            }}
          >
            <mesh position={[0, 0, -0.02]}>
              <circleGeometry args={[0.62, 32]} />
              <meshBasicMaterial color="#f43f5e" transparent opacity={0.3} />
            </mesh>
            <mesh position={[0, 0, -0.01]}>
              <circleGeometry args={[0.5, 32]} />
              <meshBasicMaterial color="#ffffff" transparent opacity={0.38} />
            </mesh>
            <mesh>
              <circleGeometry args={[0.38, 32]} />
              <meshBasicMaterial color="#ffffff" />
            </mesh>
            <mesh position={[0, -0.02, 0.01]}>
              <shapeGeometry args={[triangleShape]} />
              <meshBasicMaterial color="#ef4444" />
            </mesh>
            <mesh position={[0, 0.03, 0.02]}>
              <planeGeometry args={[0.038, 0.11]} />
              <meshBasicMaterial color="#ffffff" />
            </mesh>
            <mesh position={[0, -0.08, 0.02]}>
              <circleGeometry args={[0.022, 12]} />
              <meshBasicMaterial color="#ffffff" />
            </mesh>
          </Billboard>
        </group>
      )}
    </group>
  )
}
