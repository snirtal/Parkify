import { useEffect, useMemo } from 'react'
import { ExtrudeGeometry, Shape } from 'three'
import type { VehicleBodyType } from '../../types/parking'

export interface StylizedCar3DProps {
  colorHex: string
  accentHex: string
  bodyType: VehicleBodyType
  isHighlighted: boolean
}

function createBodyGeometry(bodyType: VehicleBodyType): ExtrudeGeometry {
  const s = new Shape()

  if (bodyType === 'SUV') {
    // Muscular modern luxury electric SUV profile (+X = front, +Y = height)
    s.moveTo(-1.78, 0.2)
    s.lineTo(1.78, 0.18)
    s.quadraticCurveTo(1.86, 0.36, 1.78, 0.62)
    s.quadraticCurveTo(1.66, 0.72, 0.88, 0.76) // sculpted hood
    s.lineTo(0.28, 1.14) // windshield A-pillar
    s.quadraticCurveTo(-0.35, 1.18, -1.42, 1.12) // long SUV roofline
    s.lineTo(-1.74, 0.76) // D-pillar tailgate
    s.quadraticCurveTo(-1.84, 0.52, -1.78, 0.2)
    s.closePath()
  } else if (bodyType === 'Crossover') {
    // Sleek fastback EV crossover profile
    s.moveTo(-1.76, 0.18)
    s.lineTo(1.78, 0.16)
    s.quadraticCurveTo(1.86, 0.34, 1.74, 0.56)
    s.quadraticCurveTo(1.52, 0.66, 0.84, 0.71)
    s.lineTo(0.22, 1.07)
    s.quadraticCurveTo(-0.48, 1.11, -1.28, 0.96)
    s.lineTo(-1.74, 0.68)
    s.quadraticCurveTo(-1.82, 0.44, -1.76, 0.18)
    s.closePath()
  } else if (bodyType === 'Coupe') {
    // Low-slung GT sports coupe profile
    s.moveTo(-1.78, 0.15)
    s.lineTo(1.82, 0.14)
    s.quadraticCurveTo(1.88, 0.28, 1.72, 0.46)
    s.quadraticCurveTo(1.42, 0.56, 0.74, 0.61)
    s.lineTo(0.14, 0.94)
    s.quadraticCurveTo(-0.42, 0.98, -1.16, 0.78)
    s.lineTo(-1.74, 0.6)
    s.quadraticCurveTo(-1.82, 0.38, -1.78, 0.15)
    s.closePath()
  } else {
    // Executive aerodynamic EV sedan profile
    s.moveTo(-1.78, 0.16)
    s.lineTo(1.8, 0.15)
    s.quadraticCurveTo(1.87, 0.31, 1.74, 0.5)
    s.quadraticCurveTo(1.48, 0.6, 0.8, 0.65)
    s.lineTo(0.2, 0.99)
    s.quadraticCurveTo(-0.45, 1.03, -1.22, 0.86)
    s.lineTo(-1.75, 0.64)
    s.quadraticCurveTo(-1.82, 0.4, -1.78, 0.16)
    s.closePath()
  }

  const depth = 1.46
  const geom = new ExtrudeGeometry(s, {
    depth,
    bevelEnabled: true,
    bevelThickness: 0.11,
    bevelSize: 0.08,
    bevelSegments: 5,
    curveSegments: 18,
  })
  geom.translate(0, 0, -depth / 2)
  geom.computeVertexNormals()
  return geom
}

function createGlasshouseGeometry(bodyType: VehicleBodyType): ExtrudeGeometry {
  const g = new Shape()

  if (bodyType === 'SUV') {
    g.moveTo(-1.42, 0.77)
    g.lineTo(0.84, 0.77)
    g.lineTo(0.26, 1.15)
    g.quadraticCurveTo(-0.35, 1.19, -1.39, 1.13)
    g.closePath()
  } else if (bodyType === 'Crossover') {
    g.moveTo(-1.32, 0.71)
    g.lineTo(0.8, 0.72)
    g.lineTo(0.2, 1.08)
    g.quadraticCurveTo(-0.48, 1.12, -1.26, 0.97)
    g.closePath()
  } else if (bodyType === 'Coupe') {
    g.moveTo(-1.2, 0.62)
    g.lineTo(0.7, 0.62)
    g.lineTo(0.12, 0.95)
    g.quadraticCurveTo(-0.42, 0.99, -1.14, 0.79)
    g.closePath()
  } else {
    g.moveTo(-1.26, 0.66)
    g.lineTo(0.76, 0.66)
    g.lineTo(0.18, 1.0)
    g.quadraticCurveTo(-0.45, 1.04, -1.2, 0.87)
    g.closePath()
  }

  const depth = 1.24
  const geom = new ExtrudeGeometry(g, {
    depth,
    bevelEnabled: true,
    bevelThickness: 0.06,
    bevelSize: 0.04,
    bevelSegments: 4,
    curveSegments: 16,
  })
  geom.translate(0, 0, -depth / 2)
  geom.computeVertexNormals()
  return geom
}

const WHEEL_OFFSETS = [
  [-0.81, 0.31, 1.14],
  [0.81, 0.31, 1.14],
  [-0.81, 0.31, -1.14],
  [0.81, 0.31, -1.14],
] as const

const SPOKE_ANGLES = [0, 1, 2, 3, 4].map((i) => (i * Math.PI * 2) / 5)

export function StylizedCar3D({
  colorHex,
  accentHex,
  bodyType,
  isHighlighted,
}: StylizedCar3DProps) {
  const bodyGeom = useMemo(() => createBodyGeometry(bodyType), [bodyType])
  const glassGeom = useMemo(() => createGlasshouseGeometry(bodyType), [bodyType])

  useEffect(() => {
    return () => {
      bodyGeom.dispose()
      glassGeom.dispose()
    }
  }, [bodyGeom, glassGeom])

  const noseY = bodyType === 'SUV' ? 0.48 : bodyType === 'Crossover' ? 0.44 : 0.39
  const tailY = bodyType === 'SUV' ? 0.64 : bodyType === 'Crossover' ? 0.58 : 0.53
  const mirrorY = bodyType === 'SUV' ? 0.78 : 0.68

  return (
    <group position={[0, 0.02, 0]}>
      {/* Ground contact shadow + subtle accent underglow */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.015, 0]}>
        <planeGeometry args={[1.86, 3.84]} />
        <meshBasicMaterial
          color={isHighlighted ? accentHex : '#040309'}
          transparent
          opacity={isHighlighted ? 0.32 : 0.72}
        />
      </mesh>

      {/* Sculpted Clearcoat Automotive Body (Ry = -90° aligns +X profile with +Z front) */}
      <mesh
        geometry={bodyGeom}
        rotation={[0, -Math.PI / 2, 0]}
        castShadow
        receiveShadow
      >
        <meshPhysicalMaterial
          color={colorHex}
          roughness={0.18}
          metalness={0.42}
          clearcoat={1}
          clearcoatRoughness={0.07}
          reflectivity={0.95}
        />
      </mesh>

      {/* Smoked Panoramic Glass Cabin & Side Windows */}
      <mesh
        geometry={glassGeom}
        rotation={[0, -Math.PI / 2, 0]}
        castShadow
      >
        <meshPhysicalMaterial
          color="#0a0d1a"
          roughness={0.05}
          metalness={0.92}
          clearcoat={1}
          clearcoatRoughness={0.04}
        />
      </mesh>

      {/* Gloss Carbon Lower Rocker Skirts & Front/Rear Splitters */}
      <mesh position={[0, 0.16, 0]}>
        <boxGeometry args={[1.68, 0.09, 3.68]} />
        <meshStandardMaterial color="#0d0c18" roughness={0.35} metalness={0.75} />
      </mesh>

      {/* Front Lower Aero Intake Grille */}
      <mesh position={[0, 0.27, 1.86]}>
        <boxGeometry args={[1.18, 0.14, 0.06]} />
        <meshStandardMaterial color="#080711" roughness={0.3} metalness={0.85} />
      </mesh>

      {/* Sculpted Dual Matrix LED Headlights + Center Lightbar */}
      <mesh position={[-0.54, noseY, 1.84]} rotation={[0, 0.14, -0.06]}>
        <boxGeometry args={[0.36, 0.065, 0.08]} />
        <meshStandardMaterial
          color="#ffffff"
          emissive="#67e8f9"
          emissiveIntensity={2.6}
        />
      </mesh>
      <mesh position={[0.54, noseY, 1.84]} rotation={[0, -0.14, 0.06]}>
        <boxGeometry args={[0.36, 0.065, 0.08]} />
        <meshStandardMaterial
          color="#ffffff"
          emissive="#67e8f9"
          emissiveIntensity={2.6}
        />
      </mesh>
      <mesh position={[0, noseY - 0.02, 1.86]}>
        <boxGeometry args={[0.74, 0.028, 0.05]} />
        <meshStandardMaterial
          color="#e0f2fe"
          emissive="#38bdf8"
          emissiveIntensity={1.8}
        />
      </mesh>

      {/* Full-Width Cyberpunk Rear LED Taillight Blade + Corner Fins */}
      <mesh position={[0, tailY, -1.85]}>
        <boxGeometry args={[1.44, 0.065, 0.06]} />
        <meshStandardMaterial
          color="#fecdd3"
          emissive="#f43f5e"
          emissiveIntensity={2.8}
        />
      </mesh>
      <mesh position={[0, 0.25, -1.86]}>
        <boxGeometry args={[1.22, 0.12, 0.06]} />
        <meshStandardMaterial color="#090814" roughness={0.35} metalness={0.8} />
      </mesh>

      {/* Aerodynamic Side-View Mirrors */}
      {([-1, 1] as const).map((side) => (
        <group key={side} position={[side * 0.82, mirrorY, 0.44]}>
          <mesh position={[-side * 0.05, -0.02, 0]} rotation={[0, 0, side * 0.35]}>
            <boxGeometry args={[0.1, 0.03, 0.04]} />
            <meshStandardMaterial color="#0f0e1c" roughness={0.3} metalness={0.8} />
          </mesh>
          <mesh>
            <boxGeometry args={[0.13, 0.075, 0.16]} />
            <meshPhysicalMaterial
              color={colorHex}
              roughness={0.2}
              metalness={0.45}
              clearcoat={1}
            />
          </mesh>
        </group>
      ))}

      {/* Four Detailed Multi-Spoke Performance Alloy Wheels + Wheel Arches */}
      {WHEEL_OFFSETS.map(([wx, wy, wz], idx) => {
        const isRight = wx > 0
        return (
          <group key={idx} position={[wx, wy, wz]}>
            {/* Dark wheel well shadow housing */}
            <mesh rotation={[0, 0, Math.PI / 2]} position={[isRight ? -0.05 : 0.05, 0.02, 0]}>
              <cylinderGeometry args={[0.35, 0.35, 0.22, 24]} />
              <meshBasicMaterial color="#05040b" />
            </mesh>

            {/* Rubber Tire */}
            <mesh rotation={[0, 0, Math.PI / 2]} castShadow>
              <cylinderGeometry args={[0.32, 0.32, 0.24, 28]} />
              <meshStandardMaterial color="#12131f" roughness={0.68} metalness={0.25} />
            </mesh>

            {/* Machined Alloy Rim Barrel */}
            <mesh
              rotation={[0, 0, Math.PI / 2]}
              position={[isRight ? 0.015 : -0.015, 0, 0]}
            >
              <cylinderGeometry args={[0.22, 0.22, 0.245, 24]} />
              <meshStandardMaterial
                color="#cbd5e1"
                roughness={0.22}
                metalness={0.88}
              />
            </mesh>

            {/* Recessed Dark Inner Rim */}
            <mesh
              rotation={[0, 0, Math.PI / 2]}
              position={[isRight ? 0.02 : -0.02, 0, 0]}
            >
              <cylinderGeometry args={[0.185, 0.185, 0.248, 20]} />
              <meshStandardMaterial color="#18162b" roughness={0.35} metalness={0.75} />
            </mesh>

            {/* 5-Spoke Star Alloy Face + Glowing Accent Hub */}
            <group position={[isRight ? 0.126 : -0.126, 0, 0]}>
              {SPOKE_ANGLES.map((ang) => (
                <mesh key={ang} rotation={[ang, 0, 0]}>
                  <boxGeometry args={[0.015, 0.36, 0.036]} />
                  <meshStandardMaterial
                    color="#e2e8f0"
                    roughness={0.18}
                    metalness={0.92}
                  />
                </mesh>
              ))}
              <mesh rotation={[0, 0, Math.PI / 2]}>
                <cylinderGeometry args={[0.055, 0.055, 0.02, 14]} />
                <meshStandardMaterial
                  color={accentHex}
                  emissive={accentHex}
                  emissiveIntensity={isHighlighted ? 1.1 : 0.45}
                />
              </mesh>
            </group>
          </group>
        )
      })}
    </group>
  )
}
