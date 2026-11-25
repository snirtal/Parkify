import { RoundedBox } from '@react-three/drei'

export function GarageArchitecture3D() {
  const bayIndices = [0, 1, 2, 3, 4, 5]
  const startX = -6.75
  const spacingX = 2.7

  return (
    <group>
      {/* Satin dark violet-charcoal garage deck with improved contrast */}
      <RoundedBox
        args={[19.6, 0.35, 15.6]}
        radius={0.12}
        smoothness={3}
        position={[0, -0.18, 0.35]}
        receiveShadow
      >
        <meshStandardMaterial
          color="#161329"
          roughness={0.38}
          metalness={0.32}
        />
      </RoundedBox>

      {/* Drive aisle subtle darker surface band for row separation */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.008, 0.35]} receiveShadow>
        <planeGeometry args={[18.2, 2.75]} />
        <meshStandardMaterial color="#100d20" roughness={0.48} metalness={0.25} />
      </mesh>

      {/* Central drive aisle glowing dashed guidance line */}
      {[-6.0, -3.0, 0, 3.0, 6.0].map((xPos) => (
        <mesh key={xPos} rotation={[-Math.PI / 2, 0, 0]} position={[xPos, 0.015, 0.35]}>
          <planeGeometry args={[1.35, 0.075]} />
          <meshBasicMaterial color="#a78bfa" transparent opacity={0.5} />
        </mesh>
      ))}

      {/* Back Architectural Wall & Garage Bay Doors */}
      <group position={[0, 0, -6.3]}>
        {/* Continuous upper structural lintel beam */}
        <mesh position={[0, 2.55, 0]} receiveShadow castShadow>
          <boxGeometry args={[18.4, 0.7, 0.55]} />
          <meshStandardMaterial color="#131024" roughness={0.45} metalness={0.4} />
        </mesh>

        {/* Overhead LED architectural light strip washing down over north row */}
        <mesh position={[0, 2.18, 0.3]}>
          <boxGeometry args={[17.8, 0.055, 0.06]} />
          <meshStandardMaterial
            color="#e9d5ff"
            emissive="#c084fc"
            emissiveIntensity={2.2}
          />
        </mesh>

        {/* Individual recessed garage bay door panels & columns */}
        {bayIndices.map((idx) => {
          const x = startX + idx * spacingX
          return (
            <group key={idx} position={[x, 0, 0]}>
              {/* Recessed metallic bay door */}
              <mesh position={[0, 1.1, -0.08]} receiveShadow>
                <boxGeometry args={[2.34, 2.2, 0.22]} />
                <meshStandardMaterial
                  color="#1f1b38"
                  roughness={0.44}
                  metalness={0.5}
                />
              </mesh>

              {/* Overhead individual bay downlight bar */}
              <mesh position={[0, 2.04, 0.14]}>
                <boxGeometry args={[1.3, 0.04, 0.08]} />
                <meshStandardMaterial
                  color="#ffffff"
                  emissive="#e0f2fe"
                  emissiveIntensity={1.9}
                />
              </mesh>

              {/* Corner 'L' bracket marker on wall */}
              <mesh position={[0.85, 0.85, 0.05]}>
                <boxGeometry args={[0.22, 0.038, 0.02]} />
                <meshBasicMaterial color="#e2e8f0" transparent opacity={0.85} />
              </mesh>
              <mesh position={[0.95, 0.95, 0.05]}>
                <boxGeometry args={[0.038, 0.22, 0.02]} />
                <meshBasicMaterial color="#e2e8f0" transparent opacity={0.85} />
              </mesh>

              {/* Structural divider column */}
              <mesh position={[-1.35, 1.1, 0.08]} castShadow receiveShadow>
                <boxGeometry args={[0.34, 2.22, 0.42]} />
                <meshStandardMaterial color="#141126" roughness={0.5} metalness={0.35} />
              </mesh>
            </group>
          )
        })}

        {/* Final right-most structural column */}
        <mesh position={[startX + 6 * spacingX - 1.35, 1.1, 0.08]} castShadow receiveShadow>
          <boxGeometry args={[0.34, 2.22, 0.42]} />
          <meshStandardMaterial color="#141126" roughness={0.5} metalness={0.35} />
        </mesh>
      </group>
    </group>
  )
}
