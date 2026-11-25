import { OrbitControls } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import type { Group } from 'three'
import type { BayVehicleInfo } from '../../types/parking'
import { StudioEnvironment3D } from '../garage3d/StudioEnvironment3D'
import { StylizedCar3D } from '../garage3d/StylizedCar3D'

export interface VehiclePreview3DProps {
  vehicle: BayVehicleInfo
  targetRotationY: number
}

function TurntablePlinthAndCar({ vehicle, targetRotationY }: VehiclePreview3DProps) {
  const groupRef = useRef<Group>(null)

  useFrame((_, delta) => {
    if (!groupRef.current) return
    const diff = targetRotationY - groupRef.current.rotation.y
    groupRef.current.rotation.y += diff * Math.min(delta * 7.5, 1)
  })

  const ringColor = vehicle.hasAlert ? '#c084fc' : vehicle.accentHex

  return (
    <group ref={groupRef} position={[0, -0.46, 0]}>
      {/* Glossy dark showroom turntable platform */}
      <mesh position={[0, -0.09, 0]} receiveShadow>
        <cylinderGeometry args={[2.18, 2.28, 0.16, 48]} />
        <meshStandardMaterial color="#120f24" roughness={0.28} metalness={0.68} />
      </mesh>

      {/* Outer glowing neon purple showroom ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, -0.02, 0]}>
        <torusGeometry args={[2.22, 0.032, 16, 64]} />
        <meshStandardMaterial
          color="#d8b4fe"
          emissive="#a855f7"
          emissiveIntensity={2.5}
        />
      </mesh>

      {/* Lower electric cyan accent ring */}
      <mesh rotation={[Math.PI / 2, 0, 0]} position={[0, -0.14, 0]}>
        <torusGeometry args={[2.28, 0.022, 14, 64]} />
        <meshStandardMaterial
          color="#67e8f9"
          emissive={ringColor}
          emissiveIntensity={2.1}
        />
      </mesh>

      <StylizedCar3D
        colorHex={vehicle.colorHex}
        accentHex={vehicle.accentHex}
        bodyType={vehicle.bodyType}
        isHighlighted
      />
    </group>
  )
}

export function VehiclePreview3D({ vehicle, targetRotationY }: VehiclePreview3DProps) {
  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [3.25, 1.48, 3.55], fov: 33 }}
      gl={{ alpha: true, antialias: true }}
    >
      <StudioEnvironment3D />
      <hemisphereLight args={['#f8fafc', '#2e1065', 1.25]} />
      <directionalLight position={[5, 8, 6]} intensity={2.2} color="#ffffff" />
      <directionalLight position={[-5, 4, -4]} intensity={1.1} color="#c084fc" />
      <pointLight position={[0, 2.5, 2]} intensity={1.6} color="#38bdf8" distance={8} />

      <OrbitControls
        enableZoom={false}
        enablePan={false}
        minPolarAngle={1.02}
        maxPolarAngle={1.42}
        target={[0, 0.08, 0]}
      />

      <TurntablePlinthAndCar vehicle={vehicle} targetRotationY={targetRotationY} />
    </Canvas>
  )
}
